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
                return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)
            else:
                return Response({'message': '请选择在你的专业下招生的导师'}, status=status.HTTP_400_BAD_REQUEST)
        except Professor.DoesNotExist:
            return Response({'message': '导师不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

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

                                    #发送订阅消息
                                    access_token = "78_1f-TRdT0Q_DJWlt2UYVIolmfKTzGCYaR_ixrJqvdItf9UD6q3ZnFRP1rKHAnpRrfhzjgUVvEc3Wlcg9s40-brEt_hqEweaRiqyHhvAawadHo6gUPiaWvIhFOqKcWJNaAAAERV"
                                    url = 'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'
                                    params = {
                                        'access_token': '78_1f-TRdT0Q_DJWlt2UYVIolmfKTzGCYaR_ixrJqvdItf9UD6q3ZnFRP1rKHAnpRrfhzjgUVvEc3Wlcg9s40-brEt_hqEweaRiqyHhvAawadHo6gUPiaWvIhFOqKcWJNaAAAERV'
                                    }
                                    data = {
                                        "touser": "osRxm5XJX9U5pGLqvT_tLEdkq8OQ",
                                        "template_id": "aV2bMEubY3p8j7-65-ddxZ9gYx5mUZVAIlFdHspqmDE",
                                        "page": "",
                                        "miniprogram_state":"formal",
                                        "data": {
                                            "phrase1": {
                                            "value": "审核结果"
                                            },
                                            "time11": {
                                            "value": "审核时间"
                                            },
                                            "thing18": {
                                            "value": "审批人"
                                            }
                                        }
                                    }
                                    response = requests.post(url, params=params, json=data)
                                    print(response)


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