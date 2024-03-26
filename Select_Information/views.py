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
        try:
            student = request.user.student  # 假设你的 User 模型有一个名为 student 的 OneToOneField

            professor_id = request.data.get('professor_id')

            # 查询导师是否存在
            professor = Professor.objects.get(id=professor_id)
            print(professor)
            # 查询导师的openid
            professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
            professor_openid = professor_wechat_account.openid
            print(professor_openid)

            # 确保学生的报考专业包含在导师的招生专业中
            student_subject = student.subject
            professor_enroll_subject = professor.enroll_subject.all()

            assert_choice = student_subject in professor_enroll_subject
            print(assert_choice)
            # 创建学生导师选择记录
            if student.is_selected:
                return Response({'message': '您已完成导师选择'}, 
                                status=status.HTTP_405_METHOD_NOT_ALLOWED)
            elif StudentProfessorChoice.objects.filter(student=student, status=3):
                return Response({'message': '您已选择导师，请等待回复'}, 
                                status=status.HTTP_409_CONFLICT)
            elif assert_choice:
                choice = StudentProfessorChoice.objects.create(
                    student=student,
                    professor=professor,
                    status=3,  # 请等待
                    chosen_by_professor=False
                )
                # 更新学生是否选好导师字段
                # student.is_selected = True
                # student.save()
                self.send_notification(professor_openid)
                return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'message': '请选择在你的专业下招生的导师'}, status=status.HTTP_400_BAD_REQUEST)
        except Professor.DoesNotExist:
            return Response({'message': '导师不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_notification(self, professor_openid):
        # 学生的openid和小程序的access_token
        access_token = "78__Ce8rE6383BT_YbCwlCnHe0lJAeJZl7nDGqsmdLNH3d2qEmwUt3fNgUEZJtE49HaPIBe_3hQokIw0RirU4ZJyFyjsZQp-FwYgF1TvlOZQhN0k1-0O-9T0KaUzFQZJBgACAQAS"  # 从某处安全地获取access_token

        # 微信小程序发送订阅消息的API endpoint
        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'

        # 构造消息数据
        # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
        data = {
            "touser": professor_openid,
            "template_id": "ofYpszNgPbZ2GO8ATfQBXobuKRuWco1DjSUrGeU8mLE",  # 你在微信小程序后台设置的模板ID
            "page": "index",  # 用户点击消息后跳转的小程序页面
            "data": {
                "phrase8": {"value": "有学生选择了您，需要您进行处理"},
                "date3": {"value": "2024-03-26"},
                "date4": {"value": "2024-03-26"}
            }
        }

        # 补充其他必要的信息，如审核时间和审批人姓名
        data["data"]["date3"]["value"] = "2024-03-26 10:00:00"  # 示例时间，应替换为实际时间
        data["data"]["date4"]["value"] = "2024-03-26 11:00:00"

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
        try:
            professor = request.user.professor
            student_id = request.data.get('student_id')
            student_type = int(request.data.get('student_type'))
            postgraduate_type = int(request.data.get('postgraduate_type'))
            operation = request.data.get('operation')

            print(operation)
            # 查询学生是否存在
            student = Student.objects.get(id=student_id)
            # 查询学生的openid
            student_wechat_account = WeChatAccount.objects.get(user=student.user_name)
            student_openid = student_wechat_account.openid
            print(student_openid)


            # 若学生已经完成导师选择
            if student.is_selected:
                return Response({'message': '该学生已完成导师选择'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            else:
                # 修改导师选择学生记录
                # 同意请求
                if operation == '1':
                    # 若为硕士
                    if student_type in [1, 2]:
                        # 若为北京专硕
                        if postgraduate_type == 1:
                            print("接受请求")
                            # 若还有名额
                            if professor.professional_quota > 0:
                                # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == 3:
                                    latest_choice.status = operation
                                    latest_choice.chosen_by_professor = True
                                    latest_choice.finish_time = timezone.now()
                                    latest_choice.save()

                                    student.is_selected = True
                                    student.save()
                                    professor.professional_quota -= 1
                                    professor.save()

                                    #修改方向已用指标信息
                                    department = professor.department
                                    department.used_professional_quota += 1
                                    department.save()

                                    self.send_notification(student_openid, 'accepted')

                                    return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                                else:
                                    return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_202_ACCEPTED)
                            else:
                                    return Response({'message': '导师北京专硕名额已满'}, status=status.HTTP_403_FORBIDDEN)
                        if postgraduate_type == 4:
                            # 若还有名额
                            if professor.professional_yt_quota > 0:
                                # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == 3:
                                    latest_choice.status = operation
                                    latest_choice.chosen_by_professor = True
                                    latest_choice.finish_time = timezone.now()
                                    latest_choice.save()

                                    student.is_selected = True
                                    student.save()
                                    professor.professional_yt_quota -= 1
                                    professor.save()

                                    #修改方向已用指标信息
                                    department = professor.department
                                    department.used_professional_yt_quota += 1
                                    department.save()

                                    self.send_notification(student_openid, 'accepted')

                                    return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                                else:
                                    return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_202_ACCEPTED)
                            else:
                                    return Response({'message': '导师烟台专硕名额已满'}, status=status.HTTP_403_FORBIDDEN)
                        # 若为学硕
                        if postgraduate_type == 2:
                            # 若还有名额
                            if professor.academic_quota > 0:
                                # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                print(latest_choice)
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == 3:
                                    latest_choice.status = operation
                                    latest_choice.chosen_by_professor = True
                                    latest_choice.finish_time = timezone.now()
                                    latest_choice.save()

                                    student.is_selected = True
                                    student.save()
                                    professor.academic_quota -= 1
                                    professor.save()

                                    #修改方向已用指标信息
                                    department = professor.department
                                    department.used_academic_quota += 1
                                    department.save()

                                    self.send_notification(student_openid, 'accepted')

                                    return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                                else:
                                    return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_202_ACCEPTED)
                            else:
                                return Response({'message': '导师学硕名额已满'}, status=status.HTTP_403_FORBIDDEN)

                    # 若为博士
                    if student_type == 3:
                        # 若还有名额
                        if professor.doctor_quota > 0:
                            # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == 3:
                                    latest_choice.status = operation
                                    latest_choice.chosen_by_professor = True
                                    latest_choice.finish_time = timezone.now()
                                    latest_choice.save()

                                    student.is_selected = True
                                    student.save()
                                    professor.doctor_quota -= 1
                                    professor.save()

                                    #修改方向已用指标信息
                                    department = professor.department
                                    department.used_doctor_quota += 1
                                    department.save()

                                    self.send_notification(student_openid, 'accepted')

                                    return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                                else:
                                    return Response({'message': '已存在等待审核的记录'}, status=status.HTTP_202_ACCEPTED)
                        else:
                            return Response({'message': '导师博士名额已满'}, status=status.HTTP_403_FORBIDDEN)
                # 拒绝请求
                elif operation == '2':
                    
                    print("拒绝请求")
                    StudentProfessorChoice.objects.filter(student=student, professor=professor).update(
                        status=operation,  # 拒绝
                        chosen_by_professor=False,
                        finish_time = timezone.now()
                    )

                    # 获取最近的一条记录
                    latest_choice = StudentProfessorChoice.objects.filter(
                        student=student, professor=professor).latest('submit_date')
                    
                    # 如果最近的记录是等待审核状态
                    if latest_choice.status == 3:
                        latest_choice.status = operation
                        latest_choice.finish_time = timezone.now()
                        latest_choice.chosen_by_professor = False
                        latest_choice.save()

                        self.send_notification(student_openid, 'rejected')
                        
                        return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                    else:
                        return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_202_ACCEPTED)

        
                else:
                    return Response({'message': '操作不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'message': '其他错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response({'message': '未知错误'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def send_notification(self, student_openid, action):
        # 学生的openid和小程序的access_token
        access_token = "78__Ce8rE6383BT_YbCwlCnHe0lJAeJZl7nDGqsmdLNH3d2qEmwUt3fNgUEZJtE49HaPIBe_3hQokIw0RirU4ZJyFyjsZQp-FwYgF1TvlOZQhN0k1-0O-9T0KaUzFQZJBgACAQAS"  # 从某处安全地获取access_token

        # 微信小程序发送订阅消息的API endpoint
        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'

        # 构造消息数据
        # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
        data = {
            "touser": student_openid,
            "template_id": "S1D5wX7_WY5BIfZqw0dEn8BQ6oqGlF_hFO73ZSmG9YI",  # 你在微信小程序后台设置的模板ID
            "page": "index",  # 用户点击消息后跳转的小程序页面
            "data": {
                "phrase5": {"value": "审核结果"},
                "date6": {"value": "2024-03-26"},
                "date7": {"value": "2024-03-26"}
            }
        }

        # 对于不同的操作，发送不同的消息
        if action == "accepted":
            data["data"]["phrase5"]["value"] = "接受"
        elif action == "rejected":
            data["data"]["phrase5"]["value"] = "拒绝"

        # 补充其他必要的信息，如审核时间和审批人姓名
        data["data"]["date6"]["value"] = "2024-03-26 10:00:00"  # 示例时间，应替换为实际时间
        data["data"]["date7"]["value"] = "2024-03-26 11:00:00"

        # 发送POST请求
        response = requests.post(url, json=data)
        response_data = response.json()

        # 检查请求是否成功
        if response_data.get("errcode") == 0:
            print("通知发送成功")
        else:
            print(f"通知发送失败: {response_data.get('errmsg')}")
        
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