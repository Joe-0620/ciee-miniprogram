from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import StudentProfessorChoiceSerializer
from Professor_Student_Manage.models import Student, Professor
from Select_Information.models import StudentProfessorChoice
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated


# Create your views here.
class SelectInformationView(APIView):
    permission_classes = [IsAuthenticated]  # 保证用户已经登录
    
    def get(self, request):
        # usertype = request.data.get('usertype')
        usertype = request.query_params.get('usertype')
        user = request.user
        

        if usertype == 'student':
            student = user.student

            try:
                student_choices = StudentProfessorChoice.objects.filter(student=student)
                serializer = StudentProfessorChoiceSerializer(student_choices, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except StudentProfessorChoice.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)

        elif usertype == 'professor':
            professor = user.professor

            try:
                student_choices = StudentProfessorChoice.objects.filter(professor=professor)
                serializer = StudentProfessorChoiceSerializer(student_choices, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except StudentProfessorChoice.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            
        return Response({'error': 'Usertype not correct'}, status=status.HTTP_400_BAD_REQUEST)
    

class StudentChooseProfessorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            student = request.user.student  # 假设你的 User 模型有一个名为 student 的 OneToOneField

            professor_id = request.data.get('professor_id')

            # 查询导师是否存在
            professor = Professor.objects.get(id=professor_id)

            # 确保学生和导师所在方向相同
            student_major_direction = student.major_direction
            professor_department = professor.department.department_name

            if student_major_direction == '1':
                student_department = "电气工程"
            elif student_major_direction == '2':
                student_department = "农业工程"
            elif student_major_direction == '3':
                student_department = "计算机学科方向一"
            elif student_major_direction == '4':
                student_department = "计算机学科方向二"
            elif student_major_direction == '5':
                student_department = "计算机学科方向三"
            elif student_major_direction == '6':
                student_department = "计算机学科方向四"

            assert_choice = (student_department == professor_department)

            # 创建学生导师选择记录
            if student.is_selected:
                return Response({'error': '您已完成导师选择'}, 
                                status=status.HTTP_405_METHOD_NOT_ALLOWED)
            elif StudentProfessorChoice.objects.filter(student=student, status='3'):
                return Response({'error': '您已选择导师，请等待回复'}, 
                                status=status.HTTP_409_CONFLICT)
            elif assert_choice:
                choice = StudentProfessorChoice.objects.create(
                    student=student,
                    professor=professor,
                    status='3',  # 请等待
                    chosen_by_professor=False
                )
                # 更新学生是否选好导师字段
                # student.is_selected = True
                # student.save()
                return Response({'message': '选择成功'}, status=status.HTTP_201_CREATED)
            return Response({'message': '请选择你的方向下的导师'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Professor.DoesNotExist:
            return Response({'error': '导师不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class ProfessorChooseStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            professor = request.user.professor
            student_id = request.data.get('student_id')
            student_type = request.data.get('student_type')
            postgraduate_type = request.data.get('postgraduate_type')
            operation = request.data.get('operation')
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
                    if student_type in ['1', '2']:
                        # 若为专硕
                        if postgraduate_type == '1':
                            # 若还有名额
                            if professor.professional_quota > 0:
                                # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == '3':
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
                                    return Response({'message': '导师专硕名额已满'}, status=status.HTTP_403_FORBIDDEN)
                        # 若为学硕
                        if postgraduate_type == '2':
                            # 若还有名额
                            if professor.academic_quota > 0:
                                # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                print(latest_choice)
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == '3':
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
                    if student_type == '3':
                        # 若还有名额
                        if professor.doctor_quota > 0:
                            # 获取最近的一条记录
                                latest_choice = StudentProfessorChoice.objects.filter(
                                    student=student, professor=professor).latest('submit_date')
                                
                                # 如果最近的记录是等待审核状态
                                if latest_choice.status == '3':
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
                    StudentProfessorChoice.objects.filter(student=student, professor=professor).update(
                        status=operation,  # 拒绝
                        chosen_by_professor=False,
                        finish_time = timezone.now()
                    )

                    # 获取最近的一条记录
                    latest_choice = StudentProfessorChoice.objects.filter(
                        student=student, professor=professor).latest('submit_date')
                    
                    # 如果最近的记录是等待审核状态
                    if latest_choice.status == '3':
                        latest_choice.status = operation
                        latest_choice.finish_time = timezone.now()
                        latest_choice.chosen_by_professor = False
                        latest_choice.save()
                        return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                    else:
                        return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_202_ACCEPTED)

        
                else:
                    return Response({'error': '操作不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Student.DoesNotExist:
            return Response({'error': '学生不存在'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
