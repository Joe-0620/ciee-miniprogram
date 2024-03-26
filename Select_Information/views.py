from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import StudentProfessorChoiceSerializer
from Professor_Student_Manage.models import Student, Professor, WeChatAccount
from Select_Information.models import StudentProfessorChoice
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from Professor_Student_Manage.serializers import StudentSerializer
from datetime import datetime
from django.core.cache import cache


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
                except ObjectDoesNotExist:
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

    def send_notification(self, professor_openid):
        # 学生的openid和小程序的access_token
        access_token = cache.get('access_token')
        # print(access_token)
        # 微信小程序发送订阅消息的API endpoint
        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'

        # 构造消息数据
        # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
        data = {
            "touser": professor_openid,
            "template_id": "38wdqTPRI4y4eyGFrE1LrZy3o2CJB99oqehwfpv_AmE",  # 你在微信小程序后台设置的模板ID
            "page": "index",  # 用户点击消息后跳转的小程序页面
            "data": {
                "thing1": {"value": "有学生选择了您"},
                "time7": {"value": "2024-03-31"}
            }
        }

        # 获取当前时间
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
            print(latest_choice)
            if latest_choice.status != 3:  # 状态不是"请等待"
                return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_409_CONFLICT)
            print("断点")
            if operation == '1':  # 同意请求
                if self.has_quota(professor, student):
                    latest_choice.status = 1  # 同意请求
                    latest_choice.chosen_by_professor = True
                    latest_choice.finish_time = timezone.now()
                    latest_choice.save()

                    student.is_selected = True
                    student.save()

                    self.update_quota(professor, student)
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

    def update_quota(self, professor, student):
        # 这里需要实现逻辑来更新名额
        # 示例逻辑，实际应用中可能会更复杂
        if student.postgraduate_type == 1:  # 专业型(北京)
            professor.professional_quota -= 1
        elif student.postgraduate_type == 4:  # 专业型(烟台)
            professor.professional_yt_quota -= 1
        elif student.postgraduate_type == 2:  # "学术型"
            professor.academic_quota -= 1
        elif student.postgraduate_type == 3:  # 博士
            professor.doctor_quota -= 1
        professor.save()

    def send_notification(self, student, action):
        # 学生的openid和小程序的access_token
        try:
            student_wechat_account = WeChatAccount.objects.get(user=student.user_name)
            student_openid = student_wechat_account.openid
            access_token = cache.get('access_token')
            if access_token and student_openid:
                # 微信小程序发送订阅消息的API endpoint
                url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'

                # 构造消息数据
                # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
                data = {
                    "touser": student_openid,
                    "template_id": "S1D5wX7_WY5BIfZqw0dEnyoYjjAtNPmz9QlfApZ9uOs",  # 你在微信小程序后台设置的模板ID
                    "page": "index",  # 用户点击消息后跳转的小程序页面
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
                # 如果选择存在并且还在等待状态，那么更改状态为已撤销
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