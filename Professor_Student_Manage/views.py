from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import UserLoginSerializer, StudentSerializer, ProfessorSerializer, StudentPartialUpdateSerializer
from .serializers import DepartmentSerializer, ProfessorPartialUpdateSerializer, ChangePasswordSerializer, StudentResumeSerializer
from Professor_Student_Manage.models import Student, Professor, Department, WeChatAccount
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser
from django.conf import settings
from django.core.files.storage import default_storage
import os
from django.core.exceptions import ObjectDoesNotExist
import requests


# 类继承自类generics.ListAPIView，这个类是Django REST Framework提供的一个基于类的视图，
# 用于实现列表查看操作。它自动处理了查询数据库并序列化数据返回，所以您只需要配置好查询集和序列化器即可。
# 通常用于展示列表数据，比如显示所有教授的信息列表。
class ProfessorListView(generics.ListAPIView):
    queryset = Professor.objects.all()
    serializer_class = ProfessorSerializer


class ProfessorAndDepartmentListView(APIView):
    def get(self, request):
        departments = Department.objects.all()
        professors = Professor.objects.all()
        
        department_serializer = DepartmentSerializer(departments, many=True)
        professor_serializer = ProfessorSerializer(professors, many=True)
        
        return Response({
            'departments': department_serializer.data,
            'professors': professor_serializer.data
        })
    

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
        del request.data['usertype']
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            user = authenticate(username=username, password=password)

            if user:
                # 第一个元素是所获取或创建的对象（Token值），
                # 第二个元素是一个布尔值，指示对象是否是新创建的（True表示新创建，False表示已存在）
                token, created = Token.objects.get_or_create(user=user)

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

                        # 将 WeChatAccount 对象与 Django 账号进行绑定
                        wechat_account.user = user
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

        serializer = ProfessorPartialUpdateSerializer(professor, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

# 修改学生信息
class UpdateStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        student = user.student

        serializer = StudentPartialUpdateSerializer(student, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        

# 退出登录
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户已经登录
    # parser_classes = (FileUploadParser,)  # 使用文件上传解析器

    def post(self, request):
        request.user.auth_token.delete()  # 删除用户的 Token
        return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
    
# 自动登录
class LoginView(APIView):
    permission_classes = [IsAuthenticated]  # 确保用户已经登录

    def post(self, request):
        
        return Response({"detail": "Successfully logged in."}, status=status.HTTP_200_OK)
    

# # 上传头像
# class UploadAvatarView(APIView):
#     permission_classes = [IsAuthenticated]  # 保证用户已经登录
#     # parser_classes = (FileUploadParser,)  # 使用文件上传解析器

#     def post(self, request):
        
#         server_url = 'https://django-ug4t-65547-4-1319836128.sh.run.tcloudbase.com'
#         # server_url = 'http://127.0.0.1:27082'
#         print(request.FILES)
#         if 'file' not in request.FILES:
#             return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

#         uploaded_file = request.FILES['file']  # 使用 'file' 字段名来接收文件
#         # file_obj = request.data['file']
#         # avatar = request.FILES['avatar']
#         user = request.user
#         usertype = request.query_params.get('usertype')

#         if usertype == 'student':
#             # 保存头像文件到用户的个人信息中
#             student = user.student
#             old_avatar_path = student.avatar.path if student.avatar else None

#             file_path = default_storage.save(f'avatars/student_{user.id}.jpg', uploaded_file)
#             student.avatar = file_path
#             student.save()
#             avatar_url = f"{server_url}{settings.MEDIA_URL}{file_path}"

#             # 删除旧头像文件
#             if old_avatar_path and os.path.exists(old_avatar_path):
#                 os.remove(old_avatar_path)

#             return Response({'success': 'Avatar uploaded successfully', 
#                                 'avatar_url': avatar_url}, status=status.HTTP_200_OK)

#         elif usertype == 'professor':
#             professor = user.professor
#             old_avatar_path = professor.avatar.path if professor.avatar else None

#             file_path = default_storage.save(f'avatars/professor_{user.id}.jpg', uploaded_file)
#             professor.avatar = file_path
#             professor.save()
#             avatar_url = f"{server_url}{settings.MEDIA_URL}{file_path}"

#             # 删除旧头像文件
#             if old_avatar_path and os.path.exists(old_avatar_path):
#                 os.remove(old_avatar_path)
            
#             return Response({'success': 'Avatar uploaded successfully', 
#                              'avatar_url': avatar_url}, status=status.HTTP_200_OK)
        
#         else:
#             return Response({'error': 'Usertype not correct'}, status=status.HTTP_400_BAD_REQUEST)
        
        # # 构造头像的URL
        # avatar_url = f'{settings.MEDIA_ROOT}{uploaded_file.url}'  # 拼接完整的URL

        # # 返回成功响应，包括头像的URL
        # return Response({'success': 'Avatar uploaded successfully', 'avatar_url': avatar_url}, 
        #                 status=status.HTTP_200_OK)


class UserLoginInfoView(APIView):
    permission_classes = [IsAuthenticated]  # 保证用户已经登录

    def get(self, request):
        usertype = request.query_params.get('usertype')  # 使用 query_params 获取参数

        if usertype == 'student':
            student = request.user.student
            user_information = Student.objects.get(id=student.id)
            return Response(StudentSerializer(user_information).data, status=status.HTTP_200_OK)
        elif usertype == 'professor':
            professor = request.user.professor
            user_information = Professor.objects.get(id=professor.id)
            return Response(ProfessorSerializer(user_information).data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid usertype'}, status=status.HTTP_401_UNAUTHORIZED)
