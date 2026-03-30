from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import UserLoginSerializer, StudentSerializer, ProfessorSerializer, ProfessorListSerializer, StudentPartialUpdateSerializer, ProfessorEnrollInfoSerializer
from .serializers import DepartmentSerializer, ProfessorPartialUpdateSerializer, ChangePasswordSerializer, StudentResumeSerializer
from .serializers import DepartmentReviewerSerializer
from Professor_Student_Manage.models import (
    Student,
    Professor,
    ProfessorProfileSection,
    Department,
    WeChatAccount,
    ProfessorMasterQuota,
    ProfessorDoctorQuota,
    ProfessorSharedQuotaPool,
    get_professor_heat_display_setting,
    get_quota_source_for_student,
)
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import FileUploadParser
from django.conf import settings
from django.core.files.storage import default_storage
import os
import json
from django.core.exceptions import ObjectDoesNotExist
import requests
from Enrollment_Manage.models import Subject
from Enrollment_Manage.serializers import SubjectSerializer
from Select_Information.models import StudentProfessorChoice, ReviewRecord
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
from django.db import transaction
from django.db import DataError, DatabaseError
from django.db.models import Count, Q, Prefetch
from django.core.cache import cache


logger = logging.getLogger('log')

WECHAT_CLOUD_ENV = os.environ.get('WECHAT_CLOUD_ENV', 'prod-2g1jrmkk21c1d283')
WECHAT_APPID = os.environ.get('WECHAT_APPID', 'wxa67ae78c4f1f6275')
WECHAT_SECRET = os.environ.get('WECHAT_SECRET', '7241b1950145a193f15b3584d50f3989')
WECHAT_API_CA_BUNDLE = os.environ.get('WECHAT_API_CA_BUNDLE')
WECHAT_API_VERIFY_SSL = os.environ.get('WECHAT_API_VERIFY_SSL', 'true').strip().lower() not in {
    '0',
    'false',
    'no',
    'off',
}


def get_wechat_request_kwargs(timeout=15):
    request_kwargs = {'timeout': timeout}
    if WECHAT_API_CA_BUNDLE:
        request_kwargs['verify'] = WECHAT_API_CA_BUNDLE
    else:
        request_kwargs['verify'] = WECHAT_API_VERIFY_SSL
    return request_kwargs


def get_wechat_access_token(force_refresh=False):
    cache_key = 'professor_student_manage_wechat_access_token'
    if not force_refresh:
        cached_token = cache.get(cache_key)
        if cached_token:
            return cached_token

    response = requests.get(
        'https://api.weixin.qq.com/cgi-bin/token',
        params={
            'grant_type': 'client_credential',
            'appid': WECHAT_APPID,
            'secret': WECHAT_SECRET,
        },
        **get_wechat_request_kwargs(timeout=15),
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get('access_token')
    if not access_token:
        raise ValueError(payload.get('errmsg') or '获取微信 access_token 失败。')

    expires_in = int(payload.get('expires_in') or 7200)
    cache.set(cache_key, access_token, timeout=max(expires_in - 300, 300))
    return access_token


def save_professor_profile_sections(professor, raw_sections):
    if isinstance(raw_sections, (list, tuple)) and len(raw_sections) == 1:
        raw_sections = raw_sections[0]

    if raw_sections in (None, '', [], '[]'):
        professor.profile_sections.all().delete()
        return

    sections = raw_sections
    if isinstance(raw_sections, str):
        sections = json.loads(raw_sections)

    if not isinstance(sections, list):
        raise ValueError('自定义模块格式不正确。')

    cleaned_sections = []
    for index, section in enumerate(sections):
        if not isinstance(section, dict):
            continue
        title = str(section.get('title') or '').strip()
        content = str(section.get('content') or '').strip()
        if not title or not content:
            continue
        cleaned_sections.append({
            'title': title[:50],
            'content': content[:1000],
            'sort_order': index,
        })

    professor.profile_sections.all().delete()
    ProfessorProfileSection.objects.bulk_create([
        ProfessorProfileSection(
            professor=professor,
            title=section['title'],
            content=section['content'],
            sort_order=section['sort_order'],
            is_active=True,
        )
        for section in cleaned_sections
    ])


# 继承自 generics.ListAPIView，用于返回导师列表数据。
# 这里主要给小程序端和后台复用导师基础列表。
# 返回结果会自动完成查询和序列化。
class ProfessorListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Professor.objects.select_related('department').prefetch_related(
        'enroll_subject',
        Prefetch(
            'master_quotas',
            queryset=ProfessorMasterQuota.objects.select_related('subject')
        ),
        Prefetch(
            'doctor_quotas',
            queryset=ProfessorDoctorQuota.objects.select_related('subject')
        ),
        Prefetch(
            'shared_quota_pools',
            queryset=ProfessorSharedQuotaPool.objects.prefetch_related('subjects')
        ),
    )
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


class GetSubjectsForFilterView(APIView):
    """
    获取所有硕士和博士专业列表，供前端筛选使用。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 获取硕士专业（学硕和专硕）
        master_subjects = Subject.objects.filter(subject_type__in=[0, 1]).order_by('subject_type', 'subject_name')
        # 获取博士专业
        doctor_subjects = Subject.objects.filter(subject_type=2).order_by('subject_name')
        
        master_serializer = SubjectSerializer(master_subjects, many=True)
        doctor_serializer = SubjectSerializer(doctor_subjects, many=True)
        
        return Response({
            'master_subjects': master_serializer.data,
            'doctor_subjects': doctor_serializer.data
        }, status=status.HTTP_200_OK)


class ProfessorAndDepartmentListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 获取分页参数
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        department_id = request.query_params.get('department_id', None)
        search_keyword = request.query_params.get('search', None)
        
        # 获取专业筛选参数（逗号分隔的专业 ID 列表）
        master_subject_ids = request.query_params.get('master_subject_ids', None)
        doctor_subject_ids = request.query_params.get('doctor_subject_ids', None)
        
        heat_setting = get_professor_heat_display_setting()
        heat_subject = None
        heat_postgraduate_type = None
        heat_student_type = None
        if hasattr(request.user, 'student'):
            heat_subject = request.user.student.subject
            heat_postgraduate_type = request.user.student.postgraduate_type
            heat_student_type = request.user.student.student_type

        # 获取所有方向
        departments = Department.objects.all()
        department_serializer = DepartmentSerializer(departments, many=True)
        
        # 根据方向筛选导师，并预加载关联数据避免 N+1 查询
        professors_query = Professor.objects.select_related('department').prefetch_related(
            'enroll_subject',  # 预加载招生专业（ManyToMany）
            Prefetch(
                'master_quotas',
                queryset=ProfessorMasterQuota.objects.select_related('subject')
            ),
            Prefetch(
                'doctor_quotas',
                queryset=ProfessorDoctorQuota.objects.select_related('subject')
            ),
            Prefetch(
                'shared_quota_pools',
                queryset=ProfessorSharedQuotaPool.objects.prefetch_related('subjects')
            ),
        ).annotate(
            pending_choice_count=Count('studentprofessorchoice', filter=Q(studentprofessorchoice__status=3), distinct=True),
            accepted_choice_count=Count('studentprofessorchoice', filter=Q(studentprofessorchoice__status=1), distinct=True),
            rejected_choice_count=Count('studentprofessorchoice', filter=Q(studentprofessorchoice__status=2), distinct=True),
        ).order_by('website_order', 'id')
        
        if department_id:
            professors_query = professors_query.filter(department_id=department_id)
        
        # 搜索功能：根据导师姓名、工号、研究方向进行模糊搜索
        if search_keyword:
            professors_query = professors_query.filter(
                Q(name__icontains=search_keyword) |
                Q(teacher_identity_id__icontains=search_keyword) |
                Q(research_areas__icontains=search_keyword)
            )
        
        # 硕士专业筛选：固定名额或共享池中命中指定专业且仍有剩余名额
        if master_subject_ids:
            master_ids = [int(id.strip()) for id in master_subject_ids.split(',') if id.strip()]
            if master_ids:
                professors_query = professors_query.filter(
                    (
                        Q(master_quotas__subject_id__in=master_ids) &
                        (Q(master_quotas__beijing_remaining_quota__gt=0) |
                         Q(master_quotas__yantai_remaining_quota__gt=0))
                    ) |
                    (
                        Q(shared_quota_pools__subjects__id__in=master_ids) &
                        Q(shared_quota_pools__quota_scope='master') &
                        Q(shared_quota_pools__remaining_quota__gt=0) &
                        Q(shared_quota_pools__is_active=True)
                    )
                ).distinct()
        
        # 博士专业筛选：固定名额或共享池中命中指定专业且仍有剩余名额
        if doctor_subject_ids:
            doctor_ids = [int(id.strip()) for id in doctor_subject_ids.split(',') if id.strip()]
            if doctor_ids:
                professors_query = professors_query.filter(
                    (
                        Q(doctor_quotas__subject_id__in=doctor_ids) &
                        Q(doctor_quotas__remaining_quota__gt=0)
                    ) |
                    (
                        Q(shared_quota_pools__subjects__id__in=doctor_ids) &
                        Q(shared_quota_pools__quota_scope='doctor') &
                        Q(shared_quota_pools__remaining_quota__gt=0) &
                        Q(shared_quota_pools__is_active=True)
                    )
                ).distinct()
        
        # 鍒嗛〉澶勭悊
        paginator = Paginator(professors_query, page_size)
        try:
            professors_page = paginator.page(page)
        except:
            professors_page = paginator.page(1)
        
        professor_serializer = ProfessorListSerializer(
            professors_page,
            many=True,
            context={
                'request': request,
                'heat_setting': heat_setting,
                'heat_subject': heat_subject,
                'heat_postgraduate_type': heat_postgraduate_type,
                'heat_student_type': heat_student_type,
            },
        )
        
        return Response({
            'departments': department_serializer.data,
            'professors': professor_serializer.data,
            'has_next': professors_page.has_next(),
            'has_previous': professors_page.has_previous(),
            'total_pages': paginator.num_pages,
            'current_page': page,
            'total_count': paginator.count
        })

        # 淇敼 professional_quota 鐨勬樉绀哄€?
        # modified_professors = []
        # for prof in professor_serializer.data:
        #     modified_prof = dict(prof)
        #     modified_prof['professional_quota'] = "鏈? if prof['professional_quota'] != 0 else "鏃?
        #     modified_professors.append(modified_prof)
        #     modified_prof['academic_quota'] = "鏈? if prof['academic_quota'] != 0 else "鏃?
        #     modified_professors.append(modified_prof)
        #     modified_prof['professional_yt_quota'] = "鏈? if prof['professional_yt_quota'] != 0 else "鏃?
        #     modified_professors.append(modified_prof)
        #     modified_prof['doctor_quota'] = "鏈? if prof['doctor_quota'] != 0 else "鏃?
        #     modified_professors.append(modified_prof)
        
        # print("modified_professors: ", len(modified_professors))

        # return Response({
        #     'departments': department_serializer.data,
        #     'professors': modified_professors  # 浣跨敤淇敼鍚庣殑鏁版嵁
        # })


class ProfessorDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        professor_id = request.query_params.get('professor_id')
        if not professor_id:
            return Response({'message': '缺少导师编号。'}, status=status.HTTP_400_BAD_REQUEST)

        professor = (
            Professor.objects.select_related('department')
            .prefetch_related(
                'enroll_subject',
                Prefetch(
                    'master_quotas',
                    queryset=ProfessorMasterQuota.objects.select_related('subject')
                ),
                Prefetch(
                    'doctor_quotas',
                    queryset=ProfessorDoctorQuota.objects.select_related('subject')
                ),
                Prefetch(
                    'shared_quota_pools',
                    queryset=ProfessorSharedQuotaPool.objects.prefetch_related('subjects')
                ),
                Prefetch(
                    'profile_sections',
                    queryset=ProfessorProfileSection.objects.filter(is_active=True).order_by('sort_order', 'id')
                ),
            )
            .filter(id=professor_id)
            .first()
        )

        if not professor:
            return Response({'message': '导师不存在。'}, status=status.HTTP_404_NOT_FOUND)

        return Response(ProfessorSerializer(professor).data, status=status.HTTP_200_OK)
    

class GetStudentResumeListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            student_id = request.query_params.get('student_id')
            student_info = Student.objects.get(id=student_id)

            user = request.user
            # 权限校验：学生只能查看自己的简历，导师只能查看和自己相关的学生材料
            if hasattr(user, 'student'):
                if user.student.id != student_info.id:
                    return Response({'error': '无权查看该学生信息'}, status=status.HTTP_403_FORBIDDEN)
            elif hasattr(user, 'professor'):
                professor = user.professor
                # 导师可查看：与自己有互选记录的学生，或当前名额体系下可招收该专业的学生
                has_choice = StudentProfessorChoice.objects.filter(
                    student=student_info, professor=professor
                ).exists()
                has_quota_source = get_quota_source_for_student(professor, student_info, remaining_only=False)[1] is not None
                if not has_choice and not has_quota_source:
                    return Response({'error': '无权查看该学生信息'}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'error': '无权访问'}, status=status.HTTP_403_FORBIDDEN)

            student_info_serializer = StudentResumeSerializer(student_info)
            
            return Response({
                'student_info': student_info_serializer.data}, status=status.HTTP_200_OK)
        except ObjectDoesNotExist:
            return Response({
                'error': '学生不存在'
            }, status=status.HTTP_404_NOT_FOUND)


# 用户登录视图
class UserLoginView(APIView):
    def post(self, request):
        try:
            usertype = request.data.get('usertype')
            code = request.data.get('code')  # 从请求中获取微信 code
            device_id = request.data.get('device_id')  # 设备唯一标识（可选）
            
            # 创建副本用于序列化校验，避免修改原始请求数据
            login_data = {
                'username': request.data.get('username'),
                'password': request.data.get('password')
            }

            serializer = UserLoginSerializer(data=login_data)
            if serializer.is_valid():
                username = serializer.validated_data['username']
                password = serializer.validated_data['password']

                user = authenticate(username=username, password=password)

                if user:
                    # 如果是学生且已放弃拟录取，则禁止再次登录
                    if usertype == 'student' and hasattr(user, 'student'):
                        if not user.student.can_login:
                            return Response(
                                {"error": "当前账号已被禁止登录，请联系管理员"},
                                status=status.HTTP_403_FORBIDDEN
                            )
                        if user.student.is_giveup:
                            return Response(
                                {"error": "您已放弃拟录取，无法再次登录，请联系招生老师"},
                                status=status.HTTP_403_FORBIDDEN
                            )

                    # 如果传入了 code，则先进行微信账号绑定检查
                    if code:
                        # 使用微信接口通过 code 换取 OpenID
                        url = 'https://api.weixin.qq.com/sns/jscode2session'
                        params = {
                            'appid': 'wxa67ae78c4f1f6275',  # 微信小程序 appid
                            'secret': '7241b1950145a193f15b3584d50f3989',  # 微信小程序 app secret
                            'js_code': code,
                            'grant_type': 'authorization_code'
                        }
                        try:
                            res = requests.get(
                                url,
                                params=params,
                                **get_wechat_request_kwargs(timeout=15),
                            )
                            res.raise_for_status()
                        except requests.exceptions.SSLError:
                            logger.exception('微信登录接口证书校验失败。')
                            return Response(
                                {'error': '微信登录服务证书校验失败，请联系管理员检查服务器证书配置'},
                                status=status.HTTP_502_BAD_GATEWAY
                            )
                        except requests.RequestException:
                            logger.exception('调用微信登录接口失败。')
                            return Response(
                                {'error': '微信登录服务暂时不可用，请稍后重试'},
                                status=status.HTTP_502_BAD_GATEWAY
                            )
                        data = res.json()
                        print(data)
                        session_key = data.get('session_key')
                        openid = data.get('openid')

                        if openid:
                            # 检查当前用户是否已绑定其他微信账号
                            existing_wechat = WeChatAccount.objects.filter(user=user).exclude(openid=openid).first()
                            if existing_wechat:
                                return Response({
                                    'error': '该账号已绑定至其他设备，请先在原设备上退出后再试'
                                }, status=status.HTTP_400_BAD_REQUEST)
                            
                            # 查找或创建与 OpenID 对应的 WeChatAccount 对象
                            wechat_account, created = WeChatAccount.objects.get_or_create(
                                openid=openid,
                                defaults={'user': user, 'session_key': session_key})

                            # 检查 WeChatAccount 关联的用户是否存在
                            if not User.objects.filter(id=wechat_account.user_id).exists():
                                # 如果关联用户不存在，则删除旧的 WeChatAccount 记录
                                wechat_account.delete()
                                # 重新创建 WeChatAccount 记录
                                wechat_account = WeChatAccount.objects.create(
                                    openid=openid,
                                    user=user,
                                    session_key=session_key
                                )

                            # 如果该微信账号已绑定其他用户，则拒绝登录
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

                    # 所有验证通过后，删除旧 Token 并生成新 Token
                    # 删除该用户已有的全部旧 Token
                    Token.objects.filter(user=user).delete()

                    # 生成新的 Token
                    token = Token.objects.create(user=user)

                    # 如果传入设备 ID，则将其和 Token 关联（可选）
                    if device_id:
                        token.device_id = device_id
                        token.save()

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
                        return Response({'error': '无效的用户类型'}, status=status.HTTP_401_UNAUTHORIZED)
                else:
                    return Response({'error': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                # 序列化器验证失败，格式化错误信息
                try:
                    error_messages = []
                    for field, errors in serializer.errors.items():
                        for error in errors:
                            error_messages.append(f"{field}: {str(error)}")
                    error_text = '; '.join(error_messages) if error_messages else '请求参数错误'
                except Exception as e:
                    error_text = '登录参数格式错误'
                    print(f"Error formatting serializer errors: {e}")
                return Response({'error': error_text}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # 捕获所有未预期异常
            print(f"Login error: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({'error': '登录服务异常，请稍后重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        
# 修改密码
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]  # 需要登录后才能修改密码

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)

        if serializer.is_valid():
            user = request.user
            old_password = serializer.validated_data['old_password']
            new_password = serializer.validated_data['new_password']

            # 校验旧密码是否正确
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
            # 获取学生 ID
            student_id = request.data.get('student_id')
            if not student_id:
                return Response({'message': '学生ID未提供'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # 获取该学生及其待导师签名的 PDF 云文件 ID
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

            # 获取学生 PDF 的下载地址
            response_data_pdf = self.get_fileid_download_url(student_pdf_file_id)
            if response_data_pdf.get("errcode") == 0:
                pdf_download_url = response_data_pdf['file_list'][0]['download_url']
                print(f"PDF 下载地址: {pdf_download_url}")
            else:
                return Response({'message': '获取 PDF 下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # signature_download_url = 'https://7072-prod-2g1jrmkk21c1d283-1319836128.tcb.qcloud.la/signature/professor/zhujian123_signature.png'
            # pdf_download_url = 'https://7072-prod-2g1jrmkk21c1d283-1319836128.tcb.qcloud.la/signature/student/S2022666_1727257165_agreement.pdf'
            # 生成包含签名和导师信息的 PDF
            try:
                self.generate_and_upload_pdf(professor, signature_download_url, pdf_download_url, student)
            except Exception as e:
                return Response({'message': f'生成或上传 PDF 失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 将 request.data 转成可修改的副本
        mutable_data = request.data.copy()
        mutable_data.pop('student_id', None)
        mutable_data.pop('professor_id', None)
        profile_sections = mutable_data.pop('profile_sections', None)
        if mutable_data.get('email', None) == '':
            mutable_data['email'] = None
        serializer = ProfessorPartialUpdateSerializer(professor, data=mutable_data, partial=True)
        if serializer.is_valid():
            try:
                professor = serializer.save()
                if profile_sections is not None:
                    save_professor_profile_sections(professor, profile_sections)
            except (ValueError, json.JSONDecodeError) as exc:
                return Response({'message': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
            except (DataError, DatabaseError):
                logger.exception('保存导师主页信息失败，可能是数据库字符集不支持输入内容。')
                return Response(
                    {'message': '保存失败，当前输入内容包含数据库暂不支持的字符，请检查是否包含表情符号或特殊字符。'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(ProfessorSerializer(professor).data, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_fileid_download_url(self, file_id):
        """
        根据 file_id 获取下载地址
        """
        access_token = get_wechat_access_token()
        url = f'https://api.weixin.qq.com/tcb/batchdownloadfile?access_token={access_token}'
        data = {
            "env": WECHAT_CLOUD_ENV,
            "file_list": [
                {
                    "fileid": file_id,
                    "max_age":7200
                }
            ]
        }

        # 发送 POST 请求
        response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
        response.raise_for_status()
        payload = response.json()
        if payload.get('errcode') == 41001:
            access_token = get_wechat_access_token(force_refresh=True)
            refresh_url = f'https://api.weixin.qq.com/tcb/batchdownloadfile?access_token={access_token}'
            response = requests.post(refresh_url, json=data, **get_wechat_request_kwargs(timeout=15))
            response.raise_for_status()
            payload = response.json()
        return payload



    def generate_and_upload_pdf(self, professor, signature_url, pdf_url, student):
        """
        生成包含签名图片和导师信息的 PDF，并上传到微信云托管
        """
        # 下载签名图片和 PDF
        signature_image = self.download_file(signature_url)
        pdf_file = self.download_file(pdf_url)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转成字符串
        timestamp_str = str(timestamp)

        # 使用 PyPDF2 等库合并签名图片和 PDF 文件
        updated_pdf_path = self.add_signature_to_pdf(pdf_file, signature_image, professor, student)
        print("完成签名")
        # 上传合并后的 PDF 文件
        cloud_path = f"signature/student/{student.candidate_number}_{timestamp_str}_signed_agreement.pdf"
        print("开始上传")
        self.upload_to_wechat_cloud(updated_pdf_path, cloud_path, student)

    def download_file(self, url):
        """
        下载文件并返回文件的二进制内容
        """
        response = requests.get(url, **get_wechat_request_kwargs(timeout=15))
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"文件下载失败，状态码: {response.status_code}")

    def add_signature_to_pdf(self, pdf_data, signature_data, professor, student):
        """
        将签名图片添加到 PDF 中，并返回带签名的 PDF 文件路径
        """
        # 将签名图片保存为临时文件
        signature_image_path = f"/app/Select_Information/tempFile/{professor.teacher_identity_id}_signature_image.png"  # 可按需调整保存路径
        with open(signature_image_path, "wb") as f:
            f.write(signature_data)
        # 使用 reportlab 和 PyPDF2 处理 PDF 与签名合并
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
        date = timezone.now().strftime("%Y 年%m 月%d 日")
        can.drawString(324, 305, date)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        existing_pdf = PdfReader(io.BytesIO(pdf_data))

        output = PdfWriter()
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            if i == 0:  # 默认只在第一页叠加签名
                page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转成字符串
        timestamp_str = str(timestamp)

        updated_pdf_path = f"/app/Select_Information/tempFile/{professor.user_name.username}_{timestamp_str}_signed_agreement.pdf"
        with open(updated_pdf_path, "wb") as f_out:
            output.write(f_out)

        return updated_pdf_path

    def upload_to_wechat_cloud(self, save_path, cloud_path, student):
        """
        上传生成的 PDF 到微信云托管
        """
        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        bucket = os.environ.get("COS_BUCKET")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        if not secret_id or not secret_key:
            raise ValueError('未配置 COS_SECRET_ID 或 COS_SECRET_KEY。')
        if not bucket:
            raise ValueError('未配置 COS_BUCKET。')

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        logger.info('UpdateProfessorView 上传签署文件: student_id=%s cloud_path=%s', student.id, cloud_path)

        try:
            access_token = get_wechat_access_token()
            url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'

            data = {
                "env": WECHAT_CLOUD_ENV,
                "path": cloud_path,
            }

            # 发送 POST 请求
            response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('errcode') == 41001:
                access_token = get_wechat_access_token(force_refresh=True)
                refresh_url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'
                response = requests.post(refresh_url, json=data, **get_wechat_request_kwargs(timeout=15))
                response.raise_for_status()
                response_data = response.json()
            if response_data.get('errcode') not in (None, 0):
                raise ValueError(response_data.get('errmsg') or '调用 tcb/uploadfile 失败。')

            cos_file_id = response_data.get('cos_file_id')
            if not cos_file_id:
                raise ValueError('微信接口未返回 cos_file_id。')

            response = client.upload_file(
                Bucket=bucket,
                LocalFilePath=save_path,
                Key=cloud_path,
                PartSize=1,
                MAXThread=10,
                EnableMD5=False,
                Metadata={
                    'x-cos-meta-fileid': cos_file_id  # 自定义元数据
                }
            )
            logger.info('UpdateProfessorView 上传成功: etag=%s', response.get('ETag'))

            # 上传成功后将路径保存到学生模型的 signature_table 字段
            file_id = response_data.get('file_id') or f'cloud://{WECHAT_CLOUD_ENV}.{bucket}/{cloud_path}'
            student.signature_table = file_id
            student.signature_table_professor_signatured = True
            student.save()
            logger.info('更新学生签署表成功: student_id=%s file_id=%s', student.id, file_id)

            # 删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                logger.info('删除临时文件成功: %s', save_path)

        except Exception as e:
            logger.exception('UpdateProfessorView 上传失败: %s', e)
            raise
        

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

            # 获取学生 PDF 的下载地址
            response_data_pdf = self.get_fileid_download_url(student_pdf_file_id)
            if response_data_pdf.get("errcode") == 0:
                pdf_download_url = response_data_pdf['file_list'][0]['download_url']
                print(f"PDF 下载地址: {pdf_download_url}")
            else:
                return Response({'message': '获取 PDF 下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                self.generate_and_upload_pdf(signature_download_url, pdf_download_url, student)
            except Exception as e:
                return Response({'message': f'生成或上传 PDF 失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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

            # 获取学生 PDF 的下载地址
            response_data_pdf = self.get_fileid_download_url(student_pdf_file_id)
            if response_data_pdf.get("errcode") == 0:
                pdf_download_url = response_data_pdf['file_list'][0]['download_url']
                print(f"PDF 下载地址: {pdf_download_url}")
            else:
                return Response({'message': '获取 PDF 下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            try:
                self.generate_and_upload_giveup_pdf(signature_download_url, pdf_download_url, student)
            except Exception as e:
                return Response({'message': f'生成或上传 PDF 失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


        # 将 request.data 转成可修改的副本
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
        access_token = get_wechat_access_token()
        url = f'https://api.weixin.qq.com/tcb/batchdownloadfile?access_token={access_token}'
        data = {
            "env": WECHAT_CLOUD_ENV,
            "file_list": [
                {
                    "fileid": file_id,
                    "max_age":7200
                }
            ]
        }

        # 发送 POST 请求
        response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
        response.raise_for_status()
        payload = response.json()
        if payload.get('errcode') == 41001:
            access_token = get_wechat_access_token(force_refresh=True)
            refresh_url = f'https://api.weixin.qq.com/tcb/batchdownloadfile?access_token={access_token}'
            response = requests.post(refresh_url, json=data, **get_wechat_request_kwargs(timeout=15))
            response.raise_for_status()
            payload = response.json()
        return payload



    def generate_and_upload_pdf(self, signature_url, pdf_url, student):
        """
        生成包含签名图片和导师信息的 PDF，并上传到微信云托管
        """
        # 下载签名图片和 PDF
        signature_image = self.download_file(signature_url)
        pdf_file = self.download_file(pdf_url)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转成字符串
        timestamp_str = str(timestamp)

        # 使用 PyPDF2 等库合并签名图片和 PDF 文件
        updated_pdf_path = self.add_signature_to_pdf(pdf_file, signature_image, student)
        print("完成签名")
        # 上传合并后的 PDF 文件
        cloud_path = f"signature/student/{student.candidate_number}_{timestamp_str}_signed_agreement.pdf"
        print("开始上传")
        self.upload_to_wechat_cloud(updated_pdf_path, cloud_path, student)

    def generate_and_upload_giveup_pdf(self, signature_url, pdf_url, student):
        """
        生成包含签名图片和导师信息的 PDF，并上传到微信云托管
        """
        # 涓嬭浇绛惧悕鍥剧墖鍜孭DF
        signature_image = self.download_file(signature_url)
        pdf_file = self.download_file(pdf_url)

        # 鑾峰彇褰撳墠鏃堕棿
        now = datetime.now()

        # 灏嗗綋鍓嶆椂闂磋浆鎹负鏃堕棿鎴?
        timestamp = int(now.timestamp())

        # 灏嗘椂闂存埑杞崲涓哄瓧绗︿覆
        timestamp_str = str(timestamp)

        # 使用 PyPDF2 等库合并签名图片和 PDF 文件
        updated_pdf_path = self.add_signature_to_giveup_pdf(pdf_file, signature_image, student)
        print("瀹屾垚绛惧悕")
        # 上传合并后的 PDF 文件
        cloud_path = f"signature/student/{student.candidate_number}_{timestamp_str}_signed_giveup_table.pdf"
        print("开始上传")
        self.upload_to_wechat_cloud_giveup(updated_pdf_path, cloud_path, student)

    def download_file(self, url):
        """
        下载文件并返回文件的二进制内容
        """
        response = requests.get(url, **get_wechat_request_kwargs(timeout=15))
        if response.status_code == 200:
            return response.content
        else:
            raise Exception(f"文件下载失败，状态码: {response.status_code}")

    def add_signature_to_pdf(self, pdf_data, signature_data, student):
        """
        将签名图片添加到 PDF 中，并返回带签名的 PDF 文件路径
        """
        # 将签名图片保存为临时文件
        signature_image_path = f"/app/Select_Information/tempFile/{student.candidate_number}_signature_image.png"  # 可按需调整保存路径
        with open(signature_image_path, "wb") as f:
            f.write(signature_data)
        # 使用 reportlab 和 PyPDF2 处理 PDF 与签名合并
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
        date = timezone.now().strftime("%Y 年%m 月%d 日")
        can.drawString(324, 485, date)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        existing_pdf = PdfReader(io.BytesIO(pdf_data))

        output = PdfWriter()
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            if i == 0:  # 默认只在第一页叠加签名
                page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)

        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转成字符串
        timestamp_str = str(timestamp)

        updated_pdf_path = f"/app/Select_Information/tempFile/{student.candidate_number}_{timestamp_str}_signed_agreement.pdf"
        with open(updated_pdf_path, "wb") as f_out:
            output.write(f_out)

        return updated_pdf_path
    
    def add_signature_to_giveup_pdf(self, pdf_data, signature_data, student):
        """
        将签名图片添加到 PDF 中，并返回带签名的 PDF 文件路径
        """
        # 将签名图片保存为临时文件
        signature_image_path = f"/app/Select_Information/tempFile/{student.candidate_number}_signature_image.png"  # 可按需调整保存路径
        with open(signature_image_path, "wb") as f:
            f.write(signature_data)
        # 使用 reportlab 和 PyPDF2 处理 PDF 与签名合并
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
        date = timezone.now().strftime("%Y 年%m 月%d 日")
        can.drawString(324, 420, date)
        can.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        existing_pdf = PdfReader(io.BytesIO(pdf_data))

        output = PdfWriter()
        for i in range(len(existing_pdf.pages)):
            page = existing_pdf.pages[i]
            if i == 0:  # 默认只在第一页叠加签名
                page.merge_page(overlay_pdf.pages[0])
            output.add_page(page)
        
        # 获取当前时间
        now = datetime.now()

        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())

        # 将时间戳转成字符串
        timestamp_str = str(timestamp)

        updated_pdf_path = f"/app/Select_Information/tempFile/{student.candidate_number}_{timestamp_str}_signed_giveup_table.pdf"
        with open(updated_pdf_path, "wb") as f_out:
            output.write(f_out)

        return updated_pdf_path

    def upload_to_wechat_cloud(self, save_path, cloud_path, student):
        """
        上传生成的 PDF 到微信云托管
        """
        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        bucket = os.environ.get("COS_BUCKET")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        if not secret_id or not secret_key:
            raise ValueError('未配置 COS_SECRET_ID 或 COS_SECRET_KEY。')
        if not bucket:
            raise ValueError('未配置 COS_BUCKET。')

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        logger.info('UpdateStudentView 上传签署文件: student_id=%s cloud_path=%s', student.id, cloud_path)

        try:
            access_token = get_wechat_access_token()
            url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'

            data = {
                "env": WECHAT_CLOUD_ENV,
                "path": cloud_path,
            }

            # 发送 POST 请求
            response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('errcode') == 41001:
                access_token = get_wechat_access_token(force_refresh=True)
                refresh_url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'
                response = requests.post(refresh_url, json=data, **get_wechat_request_kwargs(timeout=15))
                response.raise_for_status()
                response_data = response.json()
            if response_data.get('errcode') not in (None, 0):
                raise ValueError(response_data.get('errmsg') or '调用 tcb/uploadfile 失败。')

            cos_file_id = response_data.get('cos_file_id')
            if not cos_file_id:
                raise ValueError('微信接口未返回 cos_file_id。')

            response = client.upload_file(
                Bucket=bucket,
                LocalFilePath=save_path,
                Key=cloud_path,
                PartSize=1,
                MAXThread=10,
                EnableMD5=False,
                Metadata={
                    'x-cos-meta-fileid': cos_file_id  # 自定义元数据
                }
            )
            logger.info('UpdateStudentView 上传成功: etag=%s', response.get('ETag'))

            # 涓婁紶鎴愬姛鍚庡皢璺緞淇濆瓨鍒板鐢熸ā鍨嬬殑 signature_table 瀛楁
            file_id = response_data.get('file_id') or f'cloud://{WECHAT_CLOUD_ENV}.{bucket}/{cloud_path}'
            student.signature_table = file_id
            student.signature_table_student_signatured = True
            student.save()
            logger.info('更新学生签署表成功: student_id=%s file_id=%s', student.id, file_id)

            # 删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                logger.info('删除临时文件成功: %s', save_path)

        except Exception as e:
            logger.exception('UpdateStudentView 上传失败: %s', e)
            raise

    def upload_to_wechat_cloud_giveup(self, save_path, cloud_path, student):
        """
        涓婁紶鐢熸垚鐨凱DF鍒板井淇′簯鎵樼
        """
        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        bucket = os.environ.get("COS_BUCKET")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        if not secret_id or not secret_key:
            raise ValueError('未配置 COS_SECRET_ID 或 COS_SECRET_KEY。')
        if not bucket:
            raise ValueError('未配置 COS_BUCKET。')

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        logger.info('UpdateStudentView 上传放弃签署文件: student_id=%s cloud_path=%s', student.id, cloud_path)

        try:
            access_token = get_wechat_access_token()
            url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'

            data = {
                "env": WECHAT_CLOUD_ENV,
                "path": cloud_path,
            }

            # 鍙戦€丳OST璇锋眰
            response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('errcode') == 41001:
                access_token = get_wechat_access_token(force_refresh=True)
                refresh_url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'
                response = requests.post(refresh_url, json=data, **get_wechat_request_kwargs(timeout=15))
                response.raise_for_status()
                response_data = response.json()
            if response_data.get('errcode') not in (None, 0):
                raise ValueError(response_data.get('errmsg') or '调用 tcb/uploadfile 失败。')

            cos_file_id = response_data.get('cos_file_id')
            if not cos_file_id:
                raise ValueError('微信接口未返回 cos_file_id。')

            response = client.upload_file(
                Bucket=bucket,
                LocalFilePath=save_path,
                Key=cloud_path,
                PartSize=1,
                MAXThread=10,
                EnableMD5=False,
                Metadata={
                    'x-cos-meta-fileid': cos_file_id  # 鑷畾涔夊厓鏁版嵁
                }
            )
            logger.info('UpdateStudentView 放弃文件上传成功: etag=%s', response.get('ETag'))

            # 涓婁紶鎴愬姛鍚庡皢璺緞淇濆瓨鍒板鐢熸ā鍨嬬殑 signature_table 瀛楁
            file_id = response_data.get('file_id') or f'cloud://{WECHAT_CLOUD_ENV}.{bucket}/{cloud_path}'
            student.giveup_signature_table = file_id
            student.is_signate_giveup_table = True  # 放弃说明表签名成功
            student.save()
            logger.info('更新放弃签署表成功: student_id=%s file_id=%s', student.id, file_id)

            # 删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                logger.info('删除临时文件成功: %s', save_path)

        except Exception as e:
            logger.exception('UpdateStudentView 放弃文件上传失败: %s', e)
            raise
        

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

            if student.is_giveup:  # 这里也增加一层保护
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
            return Response({'error': '无效的用户类型'}, status=status.HTTP_401_UNAUTHORIZED)
        

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

            # 检查数据中是否包含 NaN，如有则替换为 0
            
            # if isnan(academic_quota):
            #     academic_quota = 0
            # if isnan(professional_quota):
            #     professional_quota = 0
            # if isnan(professional_yt_quota):
            #     professional_yt_quota = 0
            # if isnan(doctor_quota):
            #     doctor_quota = 0

            # 将获取到的数据保存到导师属性中

            # professor.academic_quota = academic_quota
            # professor.professional_quota = professional_quota
            # professor.professional_yt_quota = professional_yt_quota
            # professor.doctor_quota = doctor_quota
            professor.proposed_quota_approved = True

            # 清空导师的招生专业
            professor.enroll_subject.clear()

            # 根据 ID 列表添加新的专业
            # for subject_id in academic_select_list + professional_select_list:
            #     subject = Subject.objects.get(id=subject_id)
            #     professor.enroll_subject.add(subject)

            # 保存导师的变更
            professor.save()
            
            return Response({'message': '指标设置成功'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'message': '请求异常，请重试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DepartmentReviewersView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        departments = Department.objects.prefetch_related(
            Prefetch(
                'professor_set',
                queryset=Professor.objects.filter(
                    department_position__in=[1, 2]
                ).select_related('department').prefetch_related(
                    'enroll_subject',
                    Prefetch(
                        'master_quotas',
                        queryset=ProfessorMasterQuota.objects.select_related('subject')
                    ),
                    Prefetch(
                        'doctor_quotas',
                        queryset=ProfessorDoctorQuota.objects.select_related('subject')
                    )
                ),
                to_attr='reviewer_professors'
            )
        ).all()
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
        date = timezone.now().strftime("%Y 年%m 月%d 日")
        student_name = student.name
        student_major = student.subject.subject_name
        identity_number = student.identify_number or ''

        # 获取当前时间
        now = datetime.now()
        # 将当前时间转换为时间戳
        timestamp = int(now.timestamp())
        # 将时间戳转成字符串
        timestamp_str = str(timestamp)

        # 生成 PDF
        packet = self.create_overlay(student_name, student_major, date, identity_number)

        save_dir = '/app/Select_Information/tempFile/'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, f'{student.user_name.username}_{timestamp_str}_giveup_table.pdf')

        print("sava_path: ", save_path)

        # 将图层与现有 PDF 模板合并
        self.merge_pdfs(save_path, packet)

        print("sava file")

        # 上传到微信云托管
        cloud_path = f"signature/student/{student.user_name.username}_{timestamp_str}_giveup_table.pdf"
        self.upload_to_wechat_cloud(save_path, cloud_path, student)

    def merge_pdfs(self, save_path, overlay_pdf):
        """将生成的 PDF 图层与模板合并。"""
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

            # 将插入内容叠加到模板中
            template_page.merge_page(overlay_page)
            output.add_page(template_page)

        # 保存合并后的 PDF
        with open(save_path, "wb") as output_stream:
            output.write(output_stream)

    def create_overlay(self, name, major, date, identity_number):
        """生成 PDF 文件的动态内容。"""
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
        secret_id = os.environ.get("COS_SECRET_ID")
        secret_key = os.environ.get("COS_SECRET_KEY")
        bucket = os.environ.get("COS_BUCKET")
        region = 'ap-shanghai'
        token = None
        scheme = 'https'

        if not secret_id or not secret_key:
            raise ValueError('未配置 COS_SECRET_ID 或 COS_SECRET_KEY。')
        if not bucket:
            raise ValueError('未配置 COS_BUCKET。')

        config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
        client = CosS3Client(config)

        logger.info('CreateGiveupSignatureView 上传放弃说明表: student_id=%s cloud_path=%s', student.id, cloud_path)

        try:
            access_token = get_wechat_access_token()
            url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'

            data = {
                "env": WECHAT_CLOUD_ENV,
                "path": cloud_path,
            }

            # 发送 POST 请求
            response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
            response.raise_for_status()
            response_data = response.json()
            if response_data.get('errcode') == 41001:
                access_token = get_wechat_access_token(force_refresh=True)
                refresh_url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'
                response = requests.post(refresh_url, json=data, **get_wechat_request_kwargs(timeout=15))
                response.raise_for_status()
                response_data = response.json()
            if response_data.get('errcode') not in (None, 0):
                raise ValueError(response_data.get('errmsg') or '调用 tcb/uploadfile 失败。')

            cos_file_id = response_data.get('cos_file_id')
            if not cos_file_id:
                raise ValueError('微信接口未返回 cos_file_id。')

            # 根据文件大小自动选择简单上传或分块上传，分块上传支持断点续传
            response = client.upload_file(
                Bucket=bucket,
                LocalFilePath=save_path,
                Key=cloud_path,
                PartSize=1,
                MAXThread=10,
                EnableMD5=False,
                Metadata={
                    'x-cos-meta-fileid': cos_file_id  # 自定义元数据
                }
            )
            logger.info('CreateGiveupSignatureView 上传成功: etag=%s', response.get('ETag'))

            # 上传成功后删除本地临时文件
            if os.path.exists(save_path):
                os.remove(save_path)
                logger.info('删除临时文件成功: %s', save_path)

            # 上传成功后将路径保存到学生模型的 giveup_signature_table 字段
            file_id = response_data.get('file_id') or f'cloud://{WECHAT_CLOUD_ENV}.{bucket}/{cloud_path}'
            student.giveup_signature_table = file_id
            student.save()  # 保存更新后的学生信息
            logger.info('更新放弃说明表文件成功: student_id=%s file_id=%s', student.id, file_id)

        except Exception as e:
            logger.exception('CreateGiveupSignatureView 上传失败: %s', e)
            raise


def restore_choice_quota(choice):
    student = choice.student
    professor = choice.professor
    department = professor.department

    if choice.shared_quota_pool_id:
        shared_pool = choice.shared_quota_pool
        if shared_pool:
            shared_pool.used_quota = max(0, (shared_pool.used_quota or 0) - 1)
            shared_pool.remaining_quota = (shared_pool.remaining_quota or 0) + 1
            shared_pool.save(update_fields=['used_quota', 'remaining_quota', 'updated_at'])
        if department:
            if student.postgraduate_type == 3:
                department.used_doctor_quota = max(0, (department.used_doctor_quota or 0) - 1)
                department.save(update_fields=['used_doctor_quota'])
            elif student.postgraduate_type == 2:
                department.used_academic_quota = max(0, (department.used_academic_quota or 0) - 1)
                department.save(update_fields=['used_academic_quota'])
            elif student.postgraduate_type == 1:
                department.used_professional_quota = max(0, (department.used_professional_quota or 0) - 1)
                department.save(update_fields=['used_professional_quota'])
            elif student.postgraduate_type == 4:
                department.used_professional_yt_quota = max(0, (department.used_professional_yt_quota or 0) - 1)
                department.save(update_fields=['used_professional_yt_quota'])
        professor.save()
        return

    if student.postgraduate_type == 3:
        quota = ProfessorDoctorQuota.objects.filter(professor=professor, subject=student.subject).first()
        if quota:
            quota.used_quota = max(0, (quota.used_quota or 0) - 1)
            quota.remaining_quota = (quota.remaining_quota or 0) + 1
            quota.save(update_fields=['used_quota', 'remaining_quota'])
        if department:
            department.used_doctor_quota = max(0, (department.used_doctor_quota or 0) - 1)
            department.save(update_fields=['used_doctor_quota'])
        professor.save()
        return

    quota = ProfessorMasterQuota.objects.filter(professor=professor, subject=student.subject).first()
    if quota:
        update_fields = []
        if student.postgraduate_type in [1, 2]:
            quota.beijing_remaining_quota = (quota.beijing_remaining_quota or 0) + 1
            update_fields.append('beijing_remaining_quota')
            if department:
                if student.postgraduate_type == 2:
                    department.used_academic_quota = max(0, (department.used_academic_quota or 0) - 1)
                    department.save(update_fields=['used_academic_quota'])
                else:
                    department.used_professional_quota = max(0, (department.used_professional_quota or 0) - 1)
                    department.save(update_fields=['used_professional_quota'])
        elif student.postgraduate_type == 4:
            quota.yantai_remaining_quota = (quota.yantai_remaining_quota or 0) + 1
            update_fields.append('yantai_remaining_quota')
            if department:
                department.used_professional_yt_quota = max(0, (department.used_professional_yt_quota or 0) - 1)
                department.save(update_fields=['used_professional_yt_quota'])
        if update_fields:
            quota.save(update_fields=update_fields)
    professor.save()


def cancel_approved_choice_for_giveup(choice):
    restore_choice_quota(choice)

    student = choice.student
    professor = choice.professor

    choice.status = 5
    choice.finish_time = timezone.now()
    choice.save(update_fields=['status', 'finish_time'])

    student.is_selected = False
    student.signature_table_student_signatured = False
    student.signature_table_professor_signatured = False
    student.signature_table_review_status = 4
    student.save(
        update_fields=[
            'is_selected',
            'signature_table_student_signatured',
            'signature_table_professor_signatured',
            'signature_table_review_status',
        ]
    )

    ReviewRecord.objects.filter(student=student, professor=professor).delete()


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

        # 1.1 如果学生处于候补状态，则不允许放弃
        if student.is_alternate:
            return Response(
                {'message': '您处于候补状态，无法提交'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. 检查是否已上传放弃签字表
        if not getattr(student, "is_signate_giveup_table", False):
            return Response({'message': '请先上传放弃拟录取说明表'}, status=status.HTTP_400_BAD_REQUEST)

        # 3. 确认已签字后才允许放弃
        if student.giveup_signature_table:
            approved_choice = (
                StudentProfessorChoice.objects.select_related(
                    'professor__department',
                    'shared_quota_pool',
                )
                .filter(student=student, status=1, chosen_by_professor=True)
                .order_by('-finish_time', '-submit_date', '-id')
                .first()
            )

            if student.is_selected and not approved_choice:
                return Response(
                    {'message': '未找到该学生对应的已录取记录，暂时无法执行放弃，请联系管理员处理。'},
                    status=status.HTTP_409_CONFLICT
                )

            with transaction.atomic():
                if approved_choice:
                    cancel_approved_choice_for_giveup(approved_choice)

                student.is_giveup = True
                student.giveup_time = timezone.now()
                student.save(update_fields=['is_giveup', 'giveup_time'])

                StudentProfessorChoice.objects.filter(student=student, status=3).update(
                    status=4,
                    finish_time=timezone.now(),
                )

                subject = student.subject
                alternate_student = (
                    Student.objects.filter(
                        subject=subject,
                        admission_year=student.admission_year,
                        is_alternate=True,
                        is_giveup=False
                    )
                    .order_by("alternate_rank", "final_rank", "id")
                    .first()
                )

                if alternate_student:
                    alternate_student.is_alternate = False
                    alternate_student.alternate_rank = None
                    alternate_student.save(update_fields=['is_alternate', 'alternate_rank'])
                    remaining_alternates = Student.objects.filter(
                        subject=subject,
                        admission_year=student.admission_year,
                        is_alternate=True,
                        is_giveup=False,
                    ).order_by("alternate_rank", "final_rank", "id")
                    for index, candidate in enumerate(remaining_alternates, start=1):
                        if candidate.alternate_rank != index:
                            candidate.alternate_rank = index
                            candidate.save(update_fields=['alternate_rank'])

            if alternate_student:
                try:
                    self.send_notification(alternate_student)
                except Exception as exc:
                    logger.exception('通知候补学生递补成功失败: student_id=%s error=%s', alternate_student.id, exc)
                return Response(
                    {
                        'message': f'放弃拟录取成功，已补录候补学生 {alternate_student.name}',
                        'giveup_time': timezone.localtime(student.giveup_time).strftime('%Y-%m-%d %H:%M:%S') if student.giveup_time else '',
                    },
                    status=status.HTTP_200_OK
                )

            return Response(
                {
                    'message': '放弃拟录取成功，但该专业没有候补学生',
                    'giveup_time': timezone.localtime(student.giveup_time).strftime('%Y-%m-%d %H:%M:%S') if student.giveup_time else '',
                },
                status=status.HTTP_200_OK
            )

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
            response = requests.post(url, json=data, **get_wechat_request_kwargs(timeout=15))
            response_data = response.json()
            if response_data.get("errcode") != 0:
                print(f"通知发送失败: {response_data.get('errmsg')}")
        except WeChatAccount.DoesNotExist:
            print("学生微信账号不存在，无法发送通知。")

