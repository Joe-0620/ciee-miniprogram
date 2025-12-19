from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import UserLoginSerializer, StudentSerializer, ProfessorSerializer, ProfessorListSerializer, StudentPartialUpdateSerializer, ProfessorEnrollInfoSerializer
from .serializers import DepartmentSerializer, ProfessorPartialUpdateSerializer, ChangePasswordSerializer, StudentResumeSerializer
from .serializers import DepartmentReviewerSerializer
from Professor_Student_Manage.models import Student, Professor, Department, WeChatAccount
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser
from django.conf import settings
from django.core.files.storage import default_storage
import os
from django.core.exceptions import ObjectDoesNotExist
import requests
from Enrollment_Manage.models import Subject
from Enrollment_Manage.serializers import SubjectSerializer
from Select_Information.models import StudentProfessorChoice
from math import isnan
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from PyPDF2 import PdfReader, PdfWriter
import io
import traceback
from django.utils import timezone
from datetime import datetime
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
import sys
import logging
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q


# 类继承自类generics.ListAPIView，这个类是Django REST Framework提供的一个基于类的视图，
# 用于实现列表查看操作。它自动处理了查询数据库并序列化数据返回，所以您只需要配置好查询集和序列化器即可。
# 通常用于展示列表数据，比如显示所有教授的信息列表。
class ProfessorListView(generics.ListAPIView):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer


class ProfessorEnrollInfoView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = Subject.objects.all()
        subject_all = SubjectSerializer(queryset, many=True)

        professor_id = request.query_params.get('professor_id')
        queryset_p = Professor.objects.get(id=professor_id)
        professor_enroll_info = ProfessorEnrollInfoSerializer(queryset_p)

        return Response({
            'subjects': subject_all.data,
            'professor_enroll_info': professor_enroll_info.data,
        }, status=status.HTTP_200_OK)


class ProfessorAndDepartmentListView(APIView):
    # permission_classes = [IsAuthenticated]  # 需要登录才能修改密码

    def get(self, request):
        
        # 获取分页参数
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        department_id = request.query_params.get('department_id', None)
        search_keyword = request.query_params.get('search', None)
        
        # 获取所有方向
        departments = Department.objects.all()
        department_serializer = DepartmentSerializer(departments, many=True)
        
        # 根据方向筛选导师
        professors_query = Professor.objects.all().order_by('website_order', 'id')
        if department_id:
            professors_query = professors_query.filter(department_id=department_id)
        
        # 搜索功能：根据导师姓名、研究方向、职称等进行模糊搜索
        if search_keyword:
            professors_query = professors_query.filter(
                Q(name__icontains=search_keyword) |
                Q(research_areas__icontains=search_keyword) |
                Q(professor_title__icontains=search_keyword) |
                Q(contact_details__icontains=search_keyword)
            )
        
        # 分页处理
        paginator = Paginator(professors_query, page_size)
        try:
            professors_page = paginator.page(page)
        except:
            professors_page = paginator.page(1)
        
        professor_serializer = ProfessorListSerializer(professors_page, many=True)
        
        return Response({
            'departments': department_serializer.data,
            'professors': professor_serializer.data,
            'has_next': professors_page.has_next(),
            'has_previous': professors_page.has_previous(),
            'total_pages': paginator.num_pages,
            'current_page': page,
            'total_count': paginator.count
        })

        # 修改 professional_quota 的显示值
        # modified_professors = []
        # for prof in professor_serializer.data:
        #     modified_prof = dict(prof)
        #     modified_prof['professional_quota'] = "有" if prof['professional_quota'] != 0 else "无"
        #     modified_professors.append(modified_prof)
        #     modified_prof['academic_quota'] = "有" if prof['academic_quota'] != 0 else "无"
        #     modified_professors.append(modified_prof)
        #     modified_prof['professional_yt_quota'] = "有" if prof['professional_yt_quota'] != 0 else "无"
        #     modified_professors.append(modified_prof)
        #     modified_prof['doctor_quota'] = "有" if prof['doctor_quota'] != 0 else "无"
        #     modified_professors.append(modified_prof)
        
        # print("modified_professors: ", len(modified_professors))

        # return Response({
        #     'departments': department_serializer.data,
        #     'professors': modified_professors  # 使用修改后的数据
        # })
    

class GetStudentResumeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student_id = request.query_params.get('student_id')
            student_info = Student.objects.get(id=student_id)

            student_info_serializer = StudentResumeSerializer(student_info)
            
            return Response({
                'student_info': student_info_serializer.data}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({
                'error': 'Student not found'
            }, status=status.HTTP_404_NOT_FOUND)


# 用户登录验证试图，继承自 APIView，这个类是一个自定义的基于类的视图
class UserLoginView(APIView):
    def post(self, request):
        usertype = request.data.get('usertype')
        code = request.data.get('code')  # 从请求数据中获取微信的 code
        device_id = request.data.get('device_id')  # 设备唯一标识符（可选）
        del request.data['usertype']

        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(username=username, password=password)

            if user:
                # 如果是学生并且已放弃拟录取 → 禁止登录
                if usertype == 'student' and hasattr(user, 'student'):
                    if user.student.is_giveup:
                        return Response(
                            {"error": "您已放弃拟录取，无法再次登录，请联系招生老师"},
                            status=status.HTTP_403_FORBIDDEN
                        )

                # 删除该用户的所有旧 Token
                Token.objects.filter(user=user).delete()

                # 生成一个新的 Token
                token = Token.objects.create(user=user)

                # 如果设备 ID 存在，将其与 Token 关联（可选）
                if device_id:
                    token.device_id = device_id
                    token.save()

                if code:
                    # 使用微信的 API 将 code 换取 OpenID
                    url = 'https://api.weixin.qq.com/sns/jscode2session'
                    params = {
                        'appid': 'wxa67ae78c4f1f6275',  # 你的微信小程序的 appid
                        'secret': '7241b1950145a193f15b3584d50f3989',  # 你的微信小程序的 app secret
                        'js_code': code,
                        'grant_type': 'authorization_code'
                    }
                    res = requests.get(url, params=params)
                    data = res.json()
                    print(data)
                    session_key = data.get('session_key')
                    openid = data.get('openid')

                    if openid:
                        # 查找或创建一个与 OpenID 对应的 WeChatAccount 对象
                        wechat_account, created = WeChatAccount.objects.get_or_create(
                            openid=openid,
                            defaults={'user': user, 'session_key': session_key})

                        # 检查 WeChatAccount 的 user 是否存在
                        if not User.objects.filter(id=wechat_account.user_id).exists():
                            # 如果 user 不存在，删除该 WeChatAccount 记录
                            wechat_account.delete()
                            # 重新创建 WeChatAccount 记录
                            wechat_account = WeChatAccount.objects.create(
                                openid=openid,
                                user=user,
                                session_key=session_key
                            )

                        # 如果 WeChatAccount 已经绑定了其他用户，拒绝登录
                        if wechat_account.user != user:
                            # 返回已绑定用户的用户名
                            bound_username = wechat_account.user.username
                            return Response({
                                'error': '该微信账号已绑定其他用户: ' + bound_username,
                                'bound_username': bound_username  # 返回已绑定用户的用户名
                            }, status=status.HTTP_400_BAD_REQUEST)

                        # 更新 WeChatAccount 的 session_key
                        wechat_account.session_key = session_key
                        wechat_account.save()

                if usertype == 'student' and hasattr(user, 'student'):
                    user_information = user.student
                    return Response({'token': token.key, 
                                     'user_information': StudentSerializer(user_information).data,
                                     'user_id': user.id}, status=status.HTTP_200_OK)
                elif usertype == 'professor' and hasattr(user, 'professor'):
                    user_information = user.professor
                    return Response({'token': token.key, 
                                     'user_information': ProfessorSerializer(user_information).data,
                                     'user_id': user.id})
                else:
                    return Response({'error': 'Invalid usertype'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

# 修改密码
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]  # 需要登录才能修改密码

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # 验证旧密码是否正确
            if user.check_password(old_password):
                user.set_password(new_password)
                user.save()
                return Response({'message': '密码已成功修改'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': '旧密码不正确'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

# 修改导师信息
class UpdateProfessorView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        professor = user.professor

        # 检查是否传入了 signature_temp 字段
        signature_temp = request.data.get('signature_temp', None)
        if signature_temp:
            # 获取学生id
            student_id = request.data.get('student_id')
            if not student_id:
                return Response({'message': '学生ID未提供'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # 获取该ID的学生并获取待导师签名的pdf云端文件id
                student = Student.objects.get(id=student_id)
                student_pdf_file_id = student.signature_table
            except Student.DoesNotExist:
                return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)

            # 获取签名图片的下载地址
            response_data_signature = self.get_fileid_download_url(signature_temp)
            if response_data_signature.get("errcode") == 0:
                signature_download_url = response_data_signature['file_list'][0]['download_url']
                print(f"签名图片下载地址: {signature_download_url}")
            else:
                return Response({'message': '获取签名图片下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 获取学生PDF的下载地址
            response_data_pdf = self.get_fileid_download_url(student_pdf_file_id)
            if response_data_pdf.get("errcode") == 0:
                pdf_download_url = response_data_pdf['file_list'][0]['download_url']
                print(f"PDF下载地址: {pdf_download_url}")
            else:
                return Response({'message': '获取PDF下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # signature_download_url = 'https://7072-prod-2g1jrmkk21c1d283-1319836128.tcb.qcloud.la/signature/professor/zhujian123_signature.png'
            # pdf_download_url = 'https://7072-prod-2g1jrmkk21c1d283-1319836128.tcb.qcloud.la/signature/student/S2022666_1727257165_agreement.pdf'
            # 生成包含签名和导师信息的PDF
            try:
                self.generate_and_upload_pdf(professor, signature_download_url, pdf_download_url, student)
            except Exception as e:
                return Response({'message': f'生成或上传PDF失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 将 request.data 转换为一个可修改的字典
        mutable_data = request.data.copy()
        mutable_data.pop('student_id', None)
        mutable_data.pop('professor_id', None)
        serializer = ProfessorPartialUpdateSerializer(professor, data=mutable_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_fileid_download_url(self, file_id):
        """
        根据 file_id 获取下载地址
        """
        url = f'https://api.weixin.qq.com/tcb/batchdownloadfile'
        data = {
            "env": 'prod-2g1jrmkk21c1d283',
            "file_list": [
                {
                    "fileid": file_id,
                    "max_age":7200
                }
            ]
        }

        # 发送POST请求
        response = requests.post(url, json=data)
        return response.json()



    def generate_and_upload_pdf(self, professor, signature_url, pdf_url, student):
        """
        生成包含签名图片和导师信息的PDF，并上传到微信云托管
        """
        # 下载签名图片和PDF
        signature_image = self.download_file(signature_url)
        pdf_file = self.download_file(pdf_url)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        # 使用PyPDF2等库合并签名图片和PDF文件
        updated_pdf_path = self.add_signature_to_pdf(pdf_file, signature_image, professor, student)
        print("完成签名")
        # 上传合并后的PDF文件
        cloud_path = f"signature/student/{student.candidate_number}_{timestamp_str}_signed_agreement.pdf"
        print("开始上传")
        self.upload_to_wechat_cloud(updated_pdf_path, cloud_path, student)

    def download_file(self, url):
        """
        下载文件并返回文件的二进制内容
        """
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"文件下载失败，状态码: {response.status_code}")

    def add_signature_to_pdf(self, pdf_data, signature_data, professor, student):
        """
        将签名图片添加到PDF中，并返回包含签名的PDF文件路径
        """
        # 将签名图片保存为临时文件
        signature_image_path = f"/app/Select_Information/tempFile/{professor.teacher_identity_id}_signature_image.png"  # 你可以根据需要更改保存路径
        with open(signature_image_path, "wb") as f:
            f.write(signature_data)
        # 假设使用 reportlab 和 PyPDF2 来处理PDF和签名合并
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        try:
            # 注册支持中文的字体
            pdfmetrics.registerFont(TTFont('simsun', r'/app/Select_Information/pdfTemplate/simsun.ttc'))
            can.setFont('simsun', 12)
        except Exception as e:
            # 打印异常堆栈信息
            print("Error occurred while registering the font:")
            traceback.print_exc()

        can.drawImage(signature_image_path, 420, 320, width=100, height=50)
        can.drawString(172, 427, student.name)
        can.drawString(363, 427, student.subject.subject_name)
        date = timezone.now().strftime("%Y 年 %m 月 %d 日")
        can.drawString(324, 305, date)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        existing_pdf = PdfReader(io.BytesIO(pdf_data))

        output = PdfWriter()
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            if i == 0:  # 假设我们只在第一页添加签名
                page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        updated_pdf_path = f"/app/Select_Information/tempFile/{professor.user_name.username}_{timestamp_str}_signed_agreement.pdf"
        with open(updated_pdf_path, "wb") as f_out:
            output.write(f_out)

        return updated_pdf_path

    def upload_to_wechat_cloud(self, save_path, cloud_path, student):
        """
        上传生成的PDF到微信云托管
        """
        # 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        print("正在开始上传")

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

            # 上传成功后将路径保存到学生模型的 signature_table 字段
            student.signature_table = response_data['file_id']
            student.signature_table_professor_signatured = True
            student.save()
            print(f"文件路径已保存到学生的 signature_table: {cloud_path}")

            # 删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"本地临时文件已删除: {save_path}")

        except Exception as e:
            print(f"文件上传失败: {str(e)}")
        

# 修改学生信息
class UpdateStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        student = user.student

        # 检查是否传入了 signature_temp 字段
        signature_temp = request.data.get('signature_temp', None)
        professor_id = request.data.get('professor_id', None)

        # 学生签名意向表
        if signature_temp and professor_id != '-1':
            student_pdf_file_id = student.signature_table

            # 获取签名图片的下载地址
            response_data_signature = self.get_fileid_download_url(signature_temp)
            if response_data_signature.get("errcode") == 0:
                signature_download_url = response_data_signature['file_list'][0]['download_url']
                print(f"签名图片下载地址: {signature_download_url}")
            else:
                return Response({'message': '获取签名图片下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 获取学生PDF的下载地址
            response_data_pdf = self.get_fileid_download_url(student_pdf_file_id)
            if response_data_pdf.get("errcode") == 0:
                pdf_download_url = response_data_pdf['file_list'][0]['download_url']
                print(f"PDF下载地址: {pdf_download_url}")
            else:
                return Response({'message': '获取PDF下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                self.generate_and_upload_pdf(signature_download_url, pdf_download_url, student)
            except Exception as e:
                return Response({'message': f'生成或上传PDF失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # 学生签名放弃表
        if signature_temp and professor_id == '-1':
            student_pdf_file_id = student.giveup_signature_table

            # 获取签名图片的下载地址
            response_data_signature = self.get_fileid_download_url(signature_temp)
            if response_data_signature.get("errcode") == 0:
                signature_download_url = response_data_signature['file_list'][0]['download_url']
                print(f"签名图片下载地址: {signature_download_url}")
            else:
                return Response({'message': '获取签名图片下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 获取学生PDF的下载地址
            response_data_pdf = self.get_fileid_download_url(student_pdf_file_id)
            if response_data_pdf.get("errcode") == 0:
                pdf_download_url = response_data_pdf['file_list'][0]['download_url']
                print(f"PDF下载地址: {pdf_download_url}")
            else:
                return Response({'message': '获取PDF下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                self.generate_and_upload_giveup_pdf(signature_download_url, pdf_download_url, student)
            except Exception as e:
                return Response({'message': f'生成或上传PDF失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        # 将 request.data 转换为一个可修改的字典
        mutable_data = request.data.copy()
        mutable_data.pop('student_id', None)
        mutable_data.pop('professor_id', None)

        serializer = StudentPartialUpdateSerializer(student, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_fileid_download_url(self, file_id):
        """
        根据 file_id 获取下载地址
        """
        url = f'https://api.weixin.qq.com/tcb/batchdownloadfile'
        data = {
            "env": 'prod-2g1jrmkk21c1d283',
            "file_list": [
                {
                    "fileid": file_id,
                    "max_age":7200
                }
            ]
        }

        # 发送POST请求
        response = requests.post(url, json=data)
        return response.json()



    def generate_and_upload_pdf(self, signature_url, pdf_url, student):
        """
        生成包含签名图片和导师信息的PDF，并上传到微信云托管
        """
        # 下载签名图片和PDF
        signature_image = self.download_file(signature_url)
        pdf_file = self.download_file(pdf_url)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        # 使用PyPDF2等库合并签名图片和PDF文件
        updated_pdf_path = self.add_signature_to_pdf(pdf_file, signature_image, student)
        print("完成签名")
        # 上传合并后的PDF文件
        cloud_path = f"signature/student/{student.candidate_number}_{timestamp_str}_signed_agreement.pdf"
        print("开始上传")
        self.upload_to_wechat_cloud(updated_pdf_path, cloud_path, student)

    def generate_and_upload_giveup_pdf(self, signature_url, pdf_url, student):
        """
        生成包含签名图片和导师信息的PDF，并上传到微信云托管
        """
        # 下载签名图片和PDF
        signature_image = self.download_file(signature_url)
        pdf_file = self.download_file(pdf_url)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        # 使用PyPDF2等库合并签名图片和PDF文件
        updated_pdf_path = self.add_signature_to_giveup_pdf(pdf_file, signature_image, student)
        print("完成签名")
        # 上传合并后的PDF文件
        cloud_path = f"signature/student/{student.candidate_number}_{timestamp_str}_signed_giveup_table.pdf"
        print("开始上传")
        self.upload_to_wechat_cloud_giveup(updated_pdf_path, cloud_path, student)

    def download_file(self, url):
        """
        下载文件并返回文件的二进制内容
        """
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"文件下载失败，状态码: {response.status_code}")

    def add_signature_to_pdf(self, pdf_data, signature_data, student):
        """
        将签名图片添加到PDF中，并返回包含签名的PDF文件路径
        """
        # 将签名图片保存为临时文件
        signature_image_path = f"/app/Select_Information/tempFile/{student.candidate_number}_signature_image.png"  # 你可以根据需要更改保存路径
        with open(signature_image_path, "wb") as f:
            f.write(signature_data)
        # 假设使用 reportlab 和 PyPDF2 来处理PDF和签名合并
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        try:
            # 注册支持中文的字体
            pdfmetrics.registerFont(TTFont('simsun', r'/app/Select_Information/pdfTemplate/simsun.ttc'))
            can.setFont('simsun', 12)
        except Exception as e:
            # 打印异常堆栈信息
            print("Error occurred while registering the font:")
            traceback.print_exc()

        can.drawImage(signature_image_path, 390, 498, width=100, height=50)
        date = timezone.now().strftime("%Y 年 %m 月 %d 日")
        can.drawString(324, 485, date)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        existing_pdf = PdfReader(io.BytesIO(pdf_data))

        output = PdfWriter()
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            if i == 0:  # 假设我们只在第一页添加签名
                page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        updated_pdf_path = f"/app/Select_Information/tempFile/{student.candidate_number}_{timestamp_str}_signed_agreement.pdf"
        with open(updated_pdf_path, "wb") as f_out:
            output.write(f_out)

        return updated_pdf_path
    
    def add_signature_to_giveup_pdf(self, pdf_data, signature_data, student):
        """
        将签名图片添加到PDF中，并返回包含签名的PDF文件路径
        """
        # 将签名图片保存为临时文件
        signature_image_path = f"/app/Select_Information/tempFile/{student.candidate_number}_signature_image.png"  # 你可以根据需要更改保存路径
        with open(signature_image_path, "wb") as f:
            f.write(signature_data)
        # 假设使用 reportlab 和 PyPDF2 来处理PDF和签名合并
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        try:
            # 注册支持中文的字体
            pdfmetrics.registerFont(TTFont('simsun', r'/app/Select_Information/pdfTemplate/simsun.ttc'))
            can.setFont('simsun', 12)
        except Exception as e:
            # 打印异常堆栈信息
            print("Error occurred while registering the font:")
            traceback.print_exc()

        can.drawImage(signature_image_path, 388, 429, width=100, height=50)
        date = timezone.now().strftime("%Y 年 %m 月 %d 日")
        can.drawString(324, 420, date)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        existing_pdf = PdfReader(io.BytesIO(pdf_data))

        output = PdfWriter()
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            if i == 0:  # 假设我们只在第一页添加签名
                page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)
        
        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        updated_pdf_path = f"/app/Select_Information/tempFile/{student.candidate_number}_{timestamp_str}_signed_giveup_table.pdf"
        with open(updated_pdf_path, "wb") as f_out:
            output.write(f_out)

        return updated_pdf_path

    def upload_to_wechat_cloud(self, save_path, cloud_path, student):
        """
        上传生成的PDF到微信云托管
        """
        # 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        print("正在开始上传")

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

            # 上传成功后将路径保存到学生模型的 signature_table 字段
            student.signature_table = response_data['file_id']
            student.signature_table_student_signatured = True
            student.save()
            print(f"文件路径已保存到学生的 signature_table: {cloud_path}")

            # 删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"本地临时文件已删除: {save_path}")

        except Exception as e:
            print(f"文件上传失败: {str(e)}")

    def upload_to_wechat_cloud_giveup(self, save_path, cloud_path, student):
        """
        上传生成的PDF到微信云托管
        """
        # 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)

        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        print("正在开始上传")

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

            # 上传成功后将路径保存到学生模型的 signature_table 字段
            student.giveup_signature_table = response_data['file_id']
            student.is_signate_giveup_table = True # 放弃说明表签名成功
            student.save()
            print(f"文件路径已保存到学生的 giveup_signature_table: {cloud_path}")

            # 删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                print(f"本地临时文件已删除: {save_path}")

        except Exception as e:
            print(f"文件上传失败: {str(e)}")
        

# 退出登录
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户已经登录
    # parser_classes = (FileUploadParser,)  # 使用文件上传解析器

    def post(self, request):
        # request.user.auth_token.delete()  # 删除用户的 Token
        # return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)

        # 获取当前用户的 Token
        token_key = request.auth.key
        try:
            token = Token.objects.get(key=token_key)
            user = token.user

            # 解除微信账号绑定
            try:
                wechat_account = WeChatAccount.objects.get(user=user)
                wechat_account.delete()  # 删除与当前用户关联的 WeChatAccount 记录
            except WeChatAccount.DoesNotExist:
                pass  # 如果没有绑定微信账号，直接跳过

            # 删除 Token
            token.delete()

            # 执行 Django 的登出操作（可选）
            # logout(request)

            return Response({'message': '退出成功，微信账号已解绑'}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({'error': '无效的 Token'}, status=status.HTTP_400_BAD_REQUEST)
    
# 自动登录
class LoginView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户已经登录

    def post(self, request):
        user = request.user

        # 如果是学生用户
        if hasattr(user, 'student'):
            student = user.student
            if student.is_giveup:  # 已经放弃拟录取
                return Response(
                    {"detail": "您已放弃拟录取，无法再次登录，请联系招生老师"},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        return Response({"detail": "Successfully logged in."}, status=status.HTTP_200_OK)


class UserLoginInfoView(APIView):
    permission_classes = [IsAuthenticated]  # 保证用户已经登录

    def get(self, request):
        usertype = request.query_params.get('usertype')  # 使用 query_params 获取参数

        if usertype == 'student':
            student = request.user.student

            if student.is_giveup:  # 这里也加一层保护
                return Response(
                    {"detail": "您已放弃拟录取，无法获取登录信息，请联系招生老师"},
                    status=status.HTTP_403_FORBIDDEN
                )

            user_information = Student.objects.get(id=student.id)
            return Response(StudentSerializer(user_information).data, status=status.HTTP_200_OK)
        elif usertype == 'professor':
            professor = request.user.professor
            user_information = Professor.objects.get(id=professor.id)
            return Response(ProfessorSerializer(user_information).data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid usertype'}, status=status.HTTP_401_UNAUTHORIZED)
        

# 提交审核信息
class SubmitQuotaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            # 获取当前导师身份
            professor = request.user.professor

            # academic_quota = request.data.get('academic_quota')
            # professional_quota = request.data.get('professional_quota')
            # professional_yt_quota = request.data.get('professional_yt_quota')
            # doctor_quota = request.data.get('doctor_quota')
            academic_select_list = request.data.get('academic_select_list', [])
            professional_select_list = request.data.get('professional_select_list', [])

            # 检查数据是否包含NaN值，如果包含，将其替换为0
            
            # if isnan(academic_quota):
            #     academic_quota = 0
            # if isnan(professional_quota):
            #     professional_quota = 0
            # if isnan(professional_yt_quota):
            #     professional_yt_quota = 0
            # if isnan(doctor_quota):
            #     doctor_quota = 0

            # 将获取的数据保存到导师的属性中

            # professor.academic_quota = academic_quota
            # professor.professional_quota = professional_quota
            # professor.professional_yt_quota = professional_yt_quota
            # professor.doctor_quota = doctor_quota
            professor.proposed_quota_approved = True

            # 清空导师的招生专业
            professor.enroll_subject.clear()

            # 根据ID列表添加新的专业
            # for subject_id in academic_select_list + professional_select_list:
            #     subject = Subject.objects.get(id=subject_id)
            #     professor.enroll_subject.add(subject)

            # 保存导师的更改
            professor.save()
            
            return Response({'message': '指标设置成功'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': '请求异常，请重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DepartmentReviewersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = Department.objects.all()
        serializer = DepartmentReviewerSerializer(departments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    
class CreateGiveupSignatureView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student_id = request.data.get('student_id')

        # 查询学生是否存在
        student = Student.objects.get(id=student_id)

        print(student)

        # 生成放弃说明表
        if student.giveup_signature_table == None:
            self.generate_and_upload_giveup_signature(student)
            
            return Response({'message': '放弃拟录取成功'}, status=status.HTTP_200_OK)
        else:
            return Response({'message': '放弃拟录取已提交'}, status=status.HTTP_400_BAD_REQUEST)


    def generate_and_upload_giveup_signature(self, student):
        date = timezone.now().strftime("%Y 年 %m 月 %d 日")
        student_name = student.name
        student_major = student.subject.subject_name
        identity_number = student.identify_number or ''

        # 获取当前时间
        now = datetime.now()
        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())
        # 将时间戳转换为字符串
        timestamp_str = str(timestamp)

        # 生成 PDF
        packet = self.create_overlay(student_name, student_major, date, identity_number)

        save_dir = '/app/Select_Information/tempFile/'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, f'{student.user_name.username}_{timestamp_str}_giveup_table.pdf')

        print("sava_path: ", save_path)

        # 将图层与现有的 PDF 模板合并
        self.merge_pdfs(save_path, packet)

        print("sava file")

        # 上传到微信云托管
        cloud_path = f"signature/student/{student.user_name.username}_{timestamp_str}_giveup_table.pdf"
        self.upload_to_wechat_cloud(save_path, cloud_path, student)

    def merge_pdfs(self, save_path, overlay_pdf):
        """将生成的 PDF 图层与模板合并"""
        template_pdf_path = r'/app/Select_Information/pdfTemplate/giveup.pdf'
        
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

    def create_overlay(self, name, major, date, identity_number):
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

        can.drawString(150, 707, name)
        can.drawString(150, 683.5, major)
        can.drawString(150, 660.5, identity_number)
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
            student.giveup_signature_table = response_data['file_id']
            student.save()  # 保存更新后的学生信息
            print(f"文件路径已保存到学生的 giveup_signature_table: {cloud_path}")

        except Exception as e:
            print(f"文件上传失败: {str(e)}")

class SubmitGiveupSignatureView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        student_id = request.data.get('student_id')

        # 查询学生是否存在
        try:
            student = Student.objects.get(id=student_id)
        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)

        print(student)

        # 1.1 如果学生已完成导师互选，不允许放弃
        if student.is_selected:
            return Response(
                {'message': '您已完成师生互选，如需放弃请联系招生老师'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 1.2 如果学生是候补状态，不允许放弃
        if student.is_alternate:
            return Response(
                {'message': '您处于候补状态，无法提交'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 检查是否上传了放弃签署表
        if not getattr(student, "is_signate_giveup_table", False):
            return Response({'message': '请先上传放弃拟录取说明表'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 确认有签署表才允许放弃
        if student.giveup_signature_table:
            student.is_giveup = True
            student.save()

            # 把所有“请等待”的改成“已取消”
            waiting_choices = StudentProfessorChoice.objects.filter(student=student, status=3)
            cancelled_count = waiting_choices.update(status=4, finish_time=timezone.now())

            # 4. 候补补录逻辑
            subject = student.subject
            alternate_student = (
                Student.objects.filter(
                    subject=subject,
                    is_alternate=True,
                    is_giveup=False
                )
                .order_by("alternate_rank")
                .first()
            )

            if alternate_student:
                alternate_student.is_alternate = False
                alternate_student.alternate_rank = None
                alternate_student.save()

                self.send_notification(alternate_student)

                return Response(
                    {
                        'message': f'放弃拟录取成功，已补录候补学生 {alternate_student.name}'
                    },
                    status=status.HTTP_200_OK
                )

            return Response({'message': '放弃拟录取成功，但该专业没有候补学生'}, status=status.HTTP_200_OK)

        else:
            return Response({'message': '放弃拟录取失败，请重试'}, status=status.HTTP_400_BAD_REQUEST)

    # ================= 通知候补成功学生 =================
    def send_notification(self, student):
        try:
            student_wechat_account = WeChatAccount.objects.get(user=student.user_name)
            student_openid = student_wechat_account.openid
            if not student_openid:
                return

            url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'
            data = {
                "touser": student_openid,
                "template_id": "sB5ExrEe33Z6tRR5Gj_Qp6-F1TfnWhqHY_ZRQI-ZpKw",
                "page": "pages/profile/profile",
                "data": {
                    "phrase1": {"value": "候补成功"},
                    "thing6": {"value": student.name}
                }
            }
            response = requests.post(url, json=data)
            response_data = response.json()
            if response_data.get("errcode") != 0:
                print(f"通知发送失败: {response_data.get('errmsg')}")
        except WeChatAccount.DoesNotExist:
            print("学生微信账号不存在，无法发送通知。")