from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import StudentProfessorChoiceSerializer, SelectionTimeSerializer
from Professor_Student_Manage.models import Student, Professor, WeChatAccount
from Select_Information.models import StudentProfessorChoice, SelectionTime, ReviewRecord
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from Professor_Student_Manage.serializers import StudentSerializer
from datetime import datetime
from django.core.cache import cache
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PyPDF2 import PdfReader, PdfWriter
import traceback
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import os
import logging
from .models import ReviewRecord
from .serializers import ReviewRecordSerializer, ReviewRecordUpdateSerializer

class GetSelectionTimeView(generics.ListAPIView):
    queryset = SelectionTime.objects.all()
    serializer_class = SelectionTimeSerializer


# Create your views here.
class SelectInformationView(APIView):
    permission_classes = [IsAuthenticated]  # 保证用户已经登录
    
    def get(self, request):
        usertype = request.query_params.get('usertype')
        user = request.user

        if usertype == 'student':
            try:
                student = user.student
                student_choices = StudentProfessorChoice.objects.filter(student=student)
                serializer = StudentProfessorChoiceSerializer(student_choices, many=True)
                return Response({
                    'student_choices': serializer.data
                }, status=status.HTTP_200_OK)
            except Student.DoesNotExist:
                return Response({"message": "Student object does not exist."}, status=status.HTTP_404_NOT_FOUND)

        elif usertype == 'professor':
            try:
                professor = user.professor
                enroll_subjects = professor.enroll_subject.all()

                # Get all students who haven't chosen a professor yet and are in the subjects the professor enrolls
                students_without_professor = Student.objects.filter(is_selected=False, subject__in=enroll_subjects)
                student_serializer = StudentSerializer(students_without_professor, many=True)

                student_choices = StudentProfessorChoice.objects.filter(professor=professor)
                serializer = StudentProfessorChoiceSerializer(student_choices, many=True)
                return Response({
                    'student_choices': serializer.data,
                    'students_without_professor': student_serializer.data
                }, status=status.HTTP_200_OK)
            except Professor.DoesNotExist:
                return Response({"message": "Professor object does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        return Response({'message': 'Usertype not correct'}, status=status.HTTP_400_BAD_REQUEST)
    

class StudentChooseProfessorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # 检查互选是否开放
        now = timezone.now()
        try:
            selection_time = SelectionTime.objects.get(id=1)  # 假设只有一个SelectionTime对象
            if not (selection_time.open_time <= now <= selection_time.close_time):
                return Response({"message": "不在互选开放时间内"}, status=status.HTTP_400_BAD_REQUEST)
        except SelectionTime.DoesNotExist:
            return Response({"message": "互选时间设置不存在"}, status=status.HTTP_404_NOT_FOUND)

        student = request.user.student  # 假设你的 User 模型有一个名为 student 的 OneToOneField

        professor_id = request.data.get('professor_id')

        try:
            # 使用select_related减少数据库查询
            professor = Professor.objects.select_related('user_name').get(id=professor_id)
            print(professor)

            if student.is_selected:
                return Response({'message': '您已完成导师选择'}, 
                                status=status.HTTP_405_METHOD_NOT_ALLOWED)

            existing_choice = StudentProfessorChoice.objects.filter(student=student, status=3).exists()
            if existing_choice:
                return Response({'message': '您已选择导师，请等待回复'}, status=status.HTTP_409_CONFLICT)
            
            if not self.has_quota(professor, student):
                return Response({'message': '导师已没有名额'}, status=status.HTTP_400_BAD_REQUEST)

            if student.subject in professor.enroll_subject.all():
                StudentProfessorChoice.objects.create(
                    student=student, 
                    professor=professor, 
                    status=3)
                # 考虑使用Django信号发送通知
                # 查询导师的openid
                # 尝试查询导师的微信账号，如果存在则发送通知
                try:
                    professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
                    professor_openid = professor_wechat_account.openid
                    self.send_notification(professor_openid)  # 发送通知
                except WeChatAccount.DoesNotExist:
                    # 如果导师的微信账号不存在，则不发送通知，但选择仍然成功
                    pass
                return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'message': '请选择在你的专业下招生的导师'}, status=status.HTTP_400_BAD_REQUEST)
        except Professor.DoesNotExist:
            return Response({'message': '导师不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # 更通用的异常处理
            return Response({'message': '服务器错误，请稍后再试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    def has_quota(self, professor, student):
        # 这里需要实现逻辑来检查是否有足够的名额
        # 示例逻辑，实际应用中可能会更复杂
        if student.postgraduate_type == 1:  # 专业型(北京)
            return professor.professional_quota > 0
        elif student.postgraduate_type == 4:  # 专业型(烟台)
            return professor.professional_yt_quota > 0
        elif student.postgraduate_type == 2:  # 学术型
            return professor.academic_quota > 0
        elif student.postgraduate_type == 3:  # 博士
            return professor.doctor_quota > 0
        return False

    def send_notification(self, professor_openid):
        # 学生的openid和小程序的access_token
        # access_token = cache.get('access_token')
        # print(access_token)
        # 微信小程序发送订阅消息的API endpoint
        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

        # 构造消息数据
        # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
        data = {
            "touser": professor_openid,
            "template_id": "38wdqTPRI4y4eyGFrE1LrZy3o2CJB99oqehwfpv_AmE",  # 你在微信小程序后台设置的模板ID
            "page": "index/selectinformation",  # 用户点击消息后跳转的小程序页面
            "data": {
                "thing1": {"value": "有学生选择了您"},
                "time7": {"value": "2024-03-31"}
            }
        }

        # 获取��前时间
        current_time = datetime.now()

        # 格式化时间为 YYYY-MM-DD HH:MM:SS 格式
        formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

        # 将格式化后的时间设置为消息数据中的时间值
        data["data"]["time7"]["value"] = formatted_time

        # 发送POST请求
        response = requests.post(url, json=data)
        response_data = response.json()

        # 检查请求是否成功
        if response_data.get("errcode") == 0:
            print("通知发送成功")
        else:
            print(f"通知发送失败: {response_data.get('errmsg')}")
        

class ProfessorChooseStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        professor = request.user.professor
        student_id = request.data.get('student_id')
        operation = request.data.get('operation')
        
        try:
            # 查询学生是否存在
            student = Student.objects.get(id=student_id)

            # 若学生已经完成导师选择
            if student.is_selected:
                return Response({'message': '该学生已完成导师选择'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            
            latest_choice = StudentProfessorChoice.objects.filter(student=student, professor=professor).latest('submit_date')
            # print(latest_choice)
            if latest_choice.status != 3:  # 状态不是"请等待"
                return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_409_CONFLICT)
            if operation == '1':  # 同意请求
                if self.has_quota(professor, student):
                    # 更新选择状态
                    latest_choice.status = 1  # 同意请求
                    latest_choice.chosen_by_professor = True
                    latest_choice.finish_time = timezone.now()
                    latest_choice.save()

                    student.is_selected = True
                    student.save()
                    self.update_quota(professor, student)

                    # print("done!")
                    # 生成 PDF 并上传
                    self.generate_and_upload_pdf(student, professor)

                    self.send_notification(student, 'accepted')
                    return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                else:
                    return Response({'message': '名额已满，无法选择更多学生'}, status=status.HTTP_403_FORBIDDEN)

            elif operation == '2':  # 拒绝请求
                latest_choice.status = 2  # 拒绝请求
                latest_choice.finish_time = timezone.now()
                latest_choice.save()

                self.send_notification(student, 'rejected')
                return Response({'message': '操作成功'}, status=status.HTTP_200_OK)
            else:
                return Response({'message': '操作不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': '服务器错，请稍后再试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def generate_and_upload_pdf(self, student, professor):
        """生成包含学生和导师信息的PDF，并上传到微信云托管"""
        # 获取当前时间
        date = timezone.now().strftime("%Y 年 %m 月 %d 日")
        student_name = student.name
        student_major = student.subject.subject_name
        professor_name = professor.name

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        # print(date)
        # print(student_name)
        # print(student_major)
        # print(professor_name)

        # 生成 PDF
        packet = self.create_overlay(student_name, student_major, professor_name, date)

        save_dir = '/app/Select_Information/tempFile/'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, f'{student.user_name.username}_{timestamp_str}_agreement.pdf')

        print("sava_path: ", save_path)

        # 将图层与现有的 PDF 模板合并
        self.merge_pdfs(save_path, packet)

        print("sava file")

        # 上传到微信云托管
        cloud_path = f"signature/student/{student.user_name.username}_{timestamp_str}_agreement.pdf"
        self.upload_to_wechat_cloud(save_path, cloud_path, student)

    def merge_pdfs(self, save_path, overlay_pdf):
        """将生成的 PDF 图层与模板合并"""
        template_pdf_path = r'/app/Select_Information/pdfTemplate/template.pdf'
        
        # 读取现有的 PDF 模板
        template_pdf = PdfReader(template_pdf_path)
        output = PdfWriter()

        # 读取插入内容的 PDF
        overlay_pdf = PdfReader(overlay_pdf)

        # 合并两个 PDF
        for i in range(len(template_pdf.pages)):
            template_page = template_pdf.pages[i]
            overlay_page = overlay_pdf.pages[i]

            # 将插入内容叠加到模板上
            template_page.merge_page(overlay_page)
            output.add_page(template_page)

        # 保存合并后的 PDF
        with open(save_path, "wb") as output_stream:
            output.write(output_stream)

    def create_overlay(self, name, major, professor_name, date):
        """生成 PDF 文件的动态内容"""
        packet = io.BytesIO()
        # print("done!")
        can = canvas.Canvas(packet, pagesize=letter)

        try:
            # 注册支持中文的字体
            pdfmetrics.registerFont(TTFont('simsun', r'/app/Select_Information/pdfTemplate/simsun.ttc'))
            can.setFont('simsun', 12)
        except Exception as e:
            # 打印异常堆栈信息
            print("Error occurred while registering the font:")
            traceback.print_exc()

        can.drawString(150, 683.5, name)
        can.drawString(345, 683.5, major)
        can.drawString(490, 638, professor_name)
        # can.drawString(324, 497, date)

        can.save()
        packet.seek(0)
        # print("done4")
        return packet

    def upload_to_wechat_cloud(self, save_path, cloud_path, student):
        # 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)


        # 1. 设置用户属性, 包括 secret_id, secret_key, region 等。Appid 已在CosConfig中移除，请在参数 Bucket 中带上 Appid。Bucket 由 BucketName-Appid 组成
        secret_id = os.environ.get("COS_SECRET_ID")    # 用户的 SecretId，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
        secret_key = os.environ.get("COS_SECRET_KEY")   # 用户的 SecretKey，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
        region = 'ap-shanghai'      # 替换为用户的 region，已创建桶归属的region可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
                                # COS 支持的所有 region 列表参见 https://cloud.tencent.com/document/product/436/6224
        token = None               # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
        scheme = 'https'           # 指定使用 http/https 协议来访问 COS，默认为 https，可不填


        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        print("upload file")

        try:
            url = f'https://api.weixin.qq.com/tcb/uploadfile'

            data = {
                "env": 'prod-2g1jrmkk21c1d283',
                "path": cloud_path,
            }

            # 发送POST请求
            response = requests.post(url, json=data)
            response_data = response.json()
            print(response_data)
            # 自定义 metadata，包括 `x-cos-meta-fileid`
            # metadata = {
            #     "x-cos-meta-fileid": cloud_path
            # }
            # 根据文件大小自动选择简单上传或分块上传，分块上传具备断点续传功能。
            response = client.upload_file(
                Bucket=os.environ.get("COS_BUCKET"),
                LocalFilePath=save_path,
                Key=cloud_path,
                PartSize=1,
                MAXThread=10,
                EnableMD5=False,
                Metadata={
                    'x-cos-meta-fileid': response_data['cos_file_id']  # 自定义元数据
                }
            )
            print(f"文件上传成功: {response['ETag']}")
            # print(f"文件上传成功: {response}")
            # 上传成功后删除本地的临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"本地临时文件已删除: {save_path}")
            else:
                print(f"本地文件不存在: {save_path}")

            # 上传成功后将路径保存到学生模型的 signature_table 字段
            student.signature_table = response_data['file_id']
            student.save()  # 保存更新后的学生信息
            print(f"文件路径已保存到学生的 signature_table: {cloud_path}")

        except Exception as e:
            print(f"文件上传失败: {str(e)}")


    def has_quota(self, professor, student):
        # 封装可扩展的名额检查逻辑
        quota_mapping = {
            1: professor.professional_quota,
            4: professor.professional_yt_quota,
            2: professor.academic_quota,
            3: professor.doctor_quota
        }
        return quota_mapping.get(student.postgraduate_type, 0) > 0

    def update_quota(self, professor, student):
        # # 这里需要实现逻辑来更新名额
        # # 示例逻辑，实际应用中可能会更复杂
        # if student.postgraduate_type == 1:  # 专业型(北京)
        #     professor.professional_quota -= 1
        # elif student.postgraduate_type == 4:  # 专业型(烟台)
        #     professor.professional_yt_quota -= 1
        # elif student.postgraduate_type == 2:  # "学术型"
        #     professor.academic_quota -= 1
        # elif student.postgraduate_type == 3:  # 博士
        #     professor.doctor_quota -= 1
        # professor.save()

        # 更新名额
        quota_fields = {
            1: 'professional_quota',
            4: 'professional_yt_quota',
            2: 'academic_quota',
            3: 'doctor_quota'
        }
        quota_field = quota_fields.get(student.postgraduate_type)
        if quota_field:
            setattr(professor, quota_field, getattr(professor, quota_field) - 1)
            professor.save()

    def send_notification(self, student, action):
        # 学生的openid和小程序的access_token
        try:
            student_wechat_account = WeChatAccount.objects.get(user=student.user_name)
            student_openid = student_wechat_account.openid
            # access_token = cache.get('access_token')
            if student_openid:
                # 微信小程序发送订阅消息的API endpoint
                url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

                # 构造消息数据
                # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
                data = {
                    "touser": student_openid,
                    "template_id": "S1D5wX7_WY5BIfZqw0dEnyoYjjAtNPmz9QlfApZ9uOs",  # 你在微信小程序后台设置的模板ID
                    "page": "index/selectinformation",  # 用户点击消息后跳转的小程序页面
                    "data": {
                        "phrase5": {"value": "审核结果"},
                        "date7": {"value": timezone.now().strftime("%Y-%m-%d")}
                    }
                }
                # 对于不同的操作，发送不同的消息
                if action == "accepted":
                    data["data"]["phrase5"]["value"] = "接受"
                elif action == "rejected":
                    data["data"]["phrase5"]["value"] = "拒绝"

            # 发送POST请求
            response = requests.post(url, json=data)
            response_data = response.json()

            # 检查请求是否成功
            if response_data.get("errcode") == 0:
                print("通知发送成功")
            else:
                print(f"通知发送失败: {response_data.get('errmsg')}")
        except WeChatAccount.DoesNotExist:
            # 如果学生没有绑定微信账号信息，则不发送通知
            print("学生微信账号不存在，无法发送通知。")
        
class StudentCancelView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            student = request.user.student  # 获取当前登录的学生

            professor_id = request.data.get('professor_id')  # 获取导师的id

            # 查找学生提交的选择
            choice = StudentProfessorChoice.objects.filter(student=student, 
                                                           professor__id=professor_id, 
                                                           status=3).first()
            if choice:
                # 如���选择存在并且还在等待状态，那么更改状态为已撤销
                choice.status = 4
                choice.finish_time = timezone.now()
                choice.save()
                return Response({'message': '成功撤销选择'}, status=status.HTTP_200_OK)
            else:
                # 如果没有找到符合条件的选择，那么返回一个错误消息
                return Response({'message': '没有找到符合条件的选择'}, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SubmitSignatureFileView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        professor = request.user.professor
        student_id = request.data.get('student_id')
        file_id = request.data.get('file_id')
        review_professor_id = request.data.get('teacher_identity_id')

        if not student_id or not file_id:
            return Response({'message': '学生ID和文件ID是必需的'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            student = Student.objects.get(id=student_id)

            # 未签署不能提交
            if student.signature_table_professor_signatured == False or student.signature_table_student_signatured == False:
                return Response({'message': '互选表双方未完成签署'}, status=status.HTTP_400_BAD_REQUEST)

            # 已同意不能提交
            if student.signature_table_review_status == True:
                return Response({'message': '互选表已通过审核，请勿重复提交'}, status=status.HTTP_400_BAD_REQUEST)


            choice = StudentProfessorChoice.objects.filter(student=student, professor=professor, status=1).first()

            if not choice:
                return Response({'message': '没有找到已同意的互选记录'}, status=status.HTTP_404_NOT_FOUND)
            
            existing_record = ReviewRecord.objects.filter(
                student=student,
                professor=professor
            ).exclude(status=2).first()

            if existing_record:
                # print("existing_record: ", existing_record.status)
                if existing_record.status == 1:
                    return Response({'message': '审核已通过，无需提交'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'message': '待审核中，请勿重复提交'}, status=status.HTTP_400_BAD_REQUEST)

            # 更新学生信息  
            review_professor = Professor.objects.get(teacher_identity_id=review_professor_id)
            # print(review_professor)
            if review_professor.department_position == 0:
                return Response({'message': '该导师不是审核人'}, status=status.HTTP_400_BAD_REQUEST)

            # 创建审核记录
            review_record = ReviewRecord.objects.create(
                student=student,
                professor=professor,
                file_id=file_id,
                review_status=False,  # 初始状态为未审核
                review_time=None,
                reviewer=review_professor  # 审核人初始为空
            )

            student.signature_table_review_status = 3
            student.save()

            # 发送通知给方向审核人（假设方向审核人是一个特定的用户）
            # self.notify_department_reviewer(professor, student)

            return Response({'message': '签名表提交成功，等待审核'}, status=status.HTTP_200_OK)
        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': f'服务器错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def notify_department_reviewer(self, professor, student):
        # 这里实现通知方向审核人的逻辑
        # 可以通过发送邮件、微信通知等方式通知审核人
        pass

class ReviewerReviewRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reviewer = request.user.professor
        review_records = ReviewRecord.objects.filter(reviewer=reviewer)
        serializer = ReviewRecordSerializer(review_records, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class ReviewRecordUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review_record = ReviewRecord.objects.get(pk=pk, reviewer=request.user.professor)
            # print("request.data: ", request.data)
            review_status = request.data['status']
            # print("review_status: ", review_status)
        except ReviewRecord.DoesNotExist:
            return Response({'message': '审核记录不存在或您无权审核此记录'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ReviewRecordUpdateSerializer(review_record, data=request.data, partial=True)
        if serializer.is_valid():
            # print(request.data['status'])
            if review_status == 1:
                serializer.save(review_time=timezone.now())
                student = review_record.student
                student.signature_table_review_status = 1
                student.save()
                return Response({'message': '审核成功'}, status=status.HTTP_200_OK)
            else:
                serializer.save(review_time=timezone.now())
                student = review_record.student
                student.signature_table_review_status = 2
                student.save()
                return Response({'message': '审核成功'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)