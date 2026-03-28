# Select_Information/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests
from django.utils import timezone
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .serializers import StudentProfessorChoiceSerializer, SelectionTimeSerializer
from Professor_Student_Manage.models import (
    Student,
    Professor,
    WeChatAccount,
    ProfessorDoctorQuota,
    ProfessorMasterQuota,
    get_matching_shared_quota_pool,
    get_quota_source_for_student,
    recalculate_professor_quota_summary,
)
from Enrollment_Manage.models import Subject
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
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch

logger = logging.getLogger('log')

WECHAT_CLOUD_ENV = os.environ.get('WECHAT_CLOUD_ENV', 'prod-2g1jrmkk21c1d283')
WECHAT_APPID = os.environ.get('WECHAT_APPID', 'wxa67ae78c4f1f6275')
WECHAT_SECRET = os.environ.get('WECHAT_SECRET', '7241b1950145a193f15b3584d50f3989')


def get_wechat_access_token(force_refresh=False):
    cache_key = 'select_information_wechat_access_token'
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
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    access_token = payload.get('access_token')
    if not access_token:
        raise ValueError(payload.get('errmsg') or '获取微信 access_token 失败。')

    expires_in = int(payload.get('expires_in') or 7200)
    cache.set(cache_key, access_token, timeout=max(expires_in - 300, 300))
    return access_token


def get_selection_time_config(target):
    return SelectionTime.objects.filter(target=target).first()


def selection_time_is_open(target):
    selection_time = get_selection_time_config(target)
    if not selection_time:
        return False, None
    now = timezone.now()
    return selection_time.open_time <= now <= selection_time.close_time, selection_time


def format_selection_time_window(selection_time, action_label):
    if not selection_time:
        return f'当前未设置{action_label}时间。'
    open_time = timezone.localtime(selection_time.open_time).strftime('%Y-%m-%d %H:%M')
    close_time = timezone.localtime(selection_time.close_time).strftime('%Y-%m-%d %H:%M')
    return f'当前不在{action_label}时间内，可处理时间为 {open_time} 至 {close_time}。'


class GetSelectionTimeView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    queryset = SelectionTime.objects.all().order_by('target')
    serializer_class = SelectionTimeSerializer


# Create your views here.
# class SelectInformationView(APIView):
#     permission_classes = [IsAuthenticated]  # 保证用户已经登录
    
#     def get(self, request):
#         usertype = request.query_params.get('usertype')
#         user = request.user

#         if usertype == 'student':
#             try:
#                 student = user.student
#                 student_choices = StudentProfessorChoice.objects.filter(student=student)
#                 serializer = StudentProfessorChoiceSerializer(student_choices, many=True)
#                 return Response({
#                     'student_choices': serializer.data
#                 }, status=status.HTTP_200_OK)
#             except Student.DoesNotExist:
#                 return Response({"message": "Student object does not exist."}, status=status.HTTP_404_NOT_FOUND)

#         elif usertype == 'professor':
#             try:
#                 professor = user.professor
#                 # master_subjects = professor.enroll_subject.all()

#                 # print(master_subjects)

#                 # # 获取博士招生专业（从 ProfessorDoctorQuota）
#                 # doctor_subjects = Subject.objects.filter(
#                 #     professordoctorquota__professor=professor
#                 # ).distinct()

#                 # print(doctor_subjects)

#                 # # 合并硕士和博士专业，去重
#                 # enroll_subjects = master_subjects | doctor_subjects
#                 # enroll_subjects = enroll_subjects.distinct()

#                 # print(enroll_subjects)

#                 # # 获取硕士专业 ID（允许重复）
#                 # master_subject_ids = list(professor.enroll_subject.all().values_list('id', flat=True))
#                 # logger.debug(f"Master subject IDs: {master_subject_ids}")

#                 # === 获取硕士招生专业（从 ProfessorMasterQuota 里取） ===
#                 master_subject_ids = list(
#                     ProfessorMasterQuota.objects.filter(professor=professor)
#                     .values_list('subject_id', flat=True)
#                 )

#                 # 获取博士专业 ID（允许重复）
#                 doctor_subject_ids = list(ProfessorDoctorQuota.objects.filter(
#                     professor=professor
#                 ).values_list('subject_id', flat=True))
#                 # logger.debug(f"Doctor subject IDs: {doctor_subject_ids}")

#                 # 合并 ID 列表，保留重复
#                 all_subject_ids = master_subject_ids + doctor_subject_ids
#                 # logger.debug(f"All subject IDs (with duplicates): {all_subject_ids}")

#                 # 查询所有专业（去重，仅为 subject__in 查询）
#                 enroll_subjects = Subject.objects.filter(id__in=all_subject_ids)
#                 # logger.debug(f"Enroll subjects: {list(enroll_subjects.values('id', 'subject_name'))}")

#                 # Get all students who haven't chosen a professor yet and are in the subjects the professor enrolls
#                 students_without_professor = Student.objects.filter(
#                     is_selected=False,
#                     is_alternate=False,
#                     is_giveup=False,
#                     subject__in=enroll_subjects)
#                 student_serializer = StudentSerializer(students_without_professor, many=True)

#                 student_choices = StudentProfessorChoice.objects.filter(professor=professor)
#                 serializer = StudentProfessorChoiceSerializer(student_choices, many=True)
#                 return Response({
#                     'student_choices': serializer.data,
#                     'students_without_professor': student_serializer.data
#                 }, status=status.HTTP_200_OK)
#             except Professor.DoesNotExist:
#                 return Response({"message": "Professor object does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
#         return Response({'message': 'Usertype not correct'}, status=status.HTTP_400_BAD_REQUEST)

class SelectInformationView(APIView):
    permission_classes = [IsAuthenticated]  # 保证用户已经登录

    @staticmethod
    def _build_alternate_rank_map(students):
        """预计算候补排名映射，避免 StudentSerializer 中 N+1 查询"""
        # 收集所有有候补排名的学生的专业 ID
        subject_ids = set()
        for s in students:
            if s.alternate_rank:
                subject_ids.add(s.subject_id)
        if not subject_ids:
            return {}
        # 一次查询获取所有相关专业的候补学生
        all_alternates = Student.objects.filter(
            subject_id__in=subject_ids,
            alternate_rank__isnull=False,
            is_giveup=False
        ).order_by('subject_id', 'alternate_rank').values_list('id', 'subject_id')
        # 按专业分组计算排名
        from collections import defaultdict
        subject_groups = defaultdict(list)
        for sid, subj_id in all_alternates:
            subject_groups[subj_id].append(sid)
        rank_map = {}
        for subj_id, student_ids in subject_groups.items():
            for idx, sid in enumerate(student_ids, start=1):
                rank_map[sid] = idx
        return rank_map

    @staticmethod
    def _safe_int(value, default, minimum=1, maximum=None):
        try:
            result = int(value)
        except (TypeError, ValueError):
            result = default
        result = max(result, minimum)
        if maximum is not None:
            result = min(result, maximum)
        return result

    @staticmethod
    def _build_choice_counts(queryset):
        return {
            'wait': queryset.filter(status=3).count(),
            'accepted': queryset.filter(status=1).count(),
            'rejected': queryset.filter(status=2).count(),
        }
    
    def get(self, request):
        usertype = request.query_params.get('usertype')
        user = request.user

        if usertype == 'student':
            try:
                student = user.student
                page = self._safe_int(request.query_params.get('page', 1), 1, 1, 99999)
                choice_page_size = self._safe_int(request.query_params.get('choice_page_size', 10), 10, 1, 50)
                choice_status = self._safe_int(request.query_params.get('choice_status', 0), 0, 0, 4)

                student_choices_queryset = StudentProfessorChoice.objects.select_related(
                    'student', 'professor', 'professor__department'
                ).filter(student=student).order_by('-submit_date', '-id')

                choice_counts = {
                    'wait': student_choices_queryset.filter(status=3).count(),
                    'accepted': student_choices_queryset.filter(status=1).count(),
                    'rejected': student_choices_queryset.filter(status=2).count(),
                    'canceled': student_choices_queryset.filter(status=4).count(),
                }

                if choice_status in (1, 2, 3, 4):
                    student_choices_queryset = student_choices_queryset.filter(status=choice_status)

                paginator = Paginator(student_choices_queryset, choice_page_size)
                try:
                    student_choices_page = paginator.page(page)
                except:
                    student_choices_page = paginator.page(1)

                serializer = StudentProfessorChoiceSerializer(student_choices_page, many=True)
                return Response({
                    'student_choices': serializer.data,
                    'choice_counts': choice_counts,
                    'choice_has_next': student_choices_page.has_next(),
                    'choice_has_previous': student_choices_page.has_previous(),
                    'choice_total_pages': paginator.num_pages,
                    'choice_current_page': student_choices_page.number,
                    'choice_total_count': paginator.count,
                    'choice_page_size': choice_page_size,
                    'choice_status': choice_status,
                }, status=status.HTTP_200_OK)
            except Student.DoesNotExist:
                return Response({"message": "Student object does not exist."}, status=status.HTTP_404_NOT_FOUND)

        elif usertype == 'professor':
            try:
                professor = user.professor
                
                # 获取分页参数
                page = self._safe_int(request.query_params.get('page', 1), 1, 1, 99999)
                page_size = self._safe_int(request.query_params.get('page_size', 10), 10, 1, 50)
                choice_page_size = self._safe_int(request.query_params.get('choice_page_size', page_size), page_size, 1, 50)
                
                # 获取筛选参数
                subject_id = request.query_params.get('subject_id', None)
                search_keyword = request.query_params.get('search', None)
                choice_status = self._safe_int(request.query_params.get('choice_status', 0), 0, 0, 4)
                include_students = str(request.query_params.get('include_students', '1')).lower() not in ('0', 'false', 'no')
                
                # === 获取硕士招生专业（从 ProfessorMasterQuota 里取） ===
                master_subject_ids = list(
                    ProfessorMasterQuota.objects.filter(professor=professor)
                    .values_list('subject_id', flat=True)
                )

                # 获取博士专业 ID（允许重复）
                doctor_subject_ids = list(ProfessorDoctorQuota.objects.filter(
                    professor=professor
                ).values_list('subject_id', flat=True))

                # 合并 ID 列表，保留重复
                all_subject_ids = master_subject_ids + doctor_subject_ids

                # 查询所有专业（去重，仅为 subject__in 查询）
                enroll_subjects = Subject.objects.filter(id__in=all_subject_ids)

                student_serializer = None
                total_count = 0
                total_pages = 0
                has_next = False
                has_previous = False

                if include_students:
                    # 如果指定了专业ID或搜索关键词，使用传统分页
                    if subject_id or search_keyword:
                        students_query = Student.objects.select_related(
                            'subject'
                        ).filter(
                            is_selected=False,
                            is_alternate=False,
                            is_giveup=False,
                            subject__in=enroll_subjects
                        ).order_by('final_rank', 'id')

                        if subject_id:
                            students_query = students_query.filter(subject_id=subject_id)

                        if search_keyword:
                            students_query = students_query.filter(
                                Q(name__icontains=search_keyword) |
                                Q(candidate_number__icontains=search_keyword)
                            )

                        paginator = Paginator(students_query, page_size)
                        try:
                            students_page = paginator.page(page)
                        except:
                            students_page = paginator.page(1)

                        students_for_serializer = list(students_page)
                        alternate_rank_map = self._build_alternate_rank_map(students_for_serializer)
                        student_serializer = StudentSerializer(
                            students_page, many=True,
                            context={'alternate_rank_map': alternate_rank_map}
                        )
                        total_count = paginator.count
                        total_pages = paginator.num_pages
                        has_next = students_page.has_next()
                        has_previous = students_page.has_previous()

                    else:
                        # 每个专业按分页显示 page_size 个学生
                        students_list = []
                        offset = (page - 1) * page_size
                        has_more_data = False

                        for subject in enroll_subjects:
                            subject_students = Student.objects.select_related(
                                'subject'
                            ).filter(
                                is_selected=False,
                                is_alternate=False,
                                is_giveup=False,
                                subject=subject
                            ).order_by('final_rank', 'id')[offset:offset + page_size]

                            students_list.extend(subject_students)

                            next_page_check = Student.objects.filter(
                                is_selected=False,
                                is_alternate=False,
                                is_giveup=False,
                                subject=subject
                            )[offset + page_size:offset + page_size + 1]

                            if next_page_check.exists():
                                has_more_data = True

                        students_list.sort(key=lambda x: (x.final_rank or 0, x.id))

                        alternate_rank_map = self._build_alternate_rank_map(students_list)
                        student_serializer = StudentSerializer(
                            students_list, many=True,
                            context={'alternate_rank_map': alternate_rank_map}
                        )
                        total_count = len(students_list)
                        total_pages = 999
                        has_next = has_more_data
                        has_previous = page > 1

                # 获取导师的互选记录（使用 select_related 避免 N+1）
                student_choices_queryset = StudentProfessorChoice.objects.select_related(
                    'student', 'student__subject', 'professor', 'professor__department'
                ).filter(professor=professor).order_by('-submit_date', '-id')

                choice_counts = self._build_choice_counts(student_choices_queryset)
                if choice_status in (1, 2, 3):
                    student_choices_queryset = student_choices_queryset.filter(status=choice_status)

                choice_paginator = Paginator(student_choices_queryset, choice_page_size)
                try:
                    student_choices_page = choice_paginator.page(page)
                except:
                    student_choices_page = choice_paginator.page(1)

                choice_serializer = StudentProfessorChoiceSerializer(student_choices_page, many=True)
                
                # 获取所有招生专业信息（用于前端筛选）
                subject_list = Subject.objects.filter(id__in=all_subject_ids).distinct()
                subject_data = [{'id': s.id, 'subject_name': s.subject_name} for s in subject_list]
                
                return Response({
                    'student_choices': choice_serializer.data,
                    'students_without_professor': student_serializer.data if student_serializer else [],
                    'subjects': subject_data,  # 新增：专业列表供筛选
                    'choice_counts': choice_counts,
                    'choice_has_next': student_choices_page.has_next(),
                    'choice_has_previous': student_choices_page.has_previous(),
                    'choice_total_pages': choice_paginator.num_pages,
                    'choice_current_page': student_choices_page.number,
                    'choice_total_count': choice_paginator.count,
                    'choice_page_size': choice_page_size,
                    'choice_status': choice_status,
                    'has_next': has_next,
                    'has_previous': has_previous,
                    'total_pages': total_pages,
                    'current_page': page,
                    'total_count': total_count
                }, status=status.HTTP_200_OK)
            except Professor.DoesNotExist:
                return Response({"message": "Professor object does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        return Response({'message': 'Usertype not correct'}, status=status.HTTP_400_BAD_REQUEST)


# class StudentChooseProfessorView(APIView):
#     # print("test")
#     permission_classes = [IsAuthenticated]

#     # print("test")

#     def post(self, request):
#         # 检查互选是否开放
#         now = timezone.now()
#         try:
#             selection_time = SelectionTime.objects.get(id=2)  # 假设只有一个SelectionTime对象
#             if not (selection_time.open_time <= now <= selection_time.close_time):
#                 return Response({"message": "不在互选开放时间内"}, status=status.HTTP_400_BAD_REQUEST)
#         except SelectionTime.DoesNotExist:
#             # print("test")
#             return Response({"message": "互选时间设置不存在"}, status=status.HTTP_404_NOT_FOUND)

#         student = request.user.student  # 假设你的 User 模型有一个名为 student 的 OneToOneField

#         professor_id = request.data.get('professor_id')

#         try:
#             # print("test")
#             # 使用select_related减少数据库查询
#             professor = Professor.objects.select_related('user_name').get(id=professor_id)
#             # print(professor)

#             if student.is_selected:
#                 return Response({'message': '您已完成导师选择'}, 
#                                 status=status.HTTP_405_METHOD_NOT_ALLOWED)

#             existing_choice = StudentProfessorChoice.objects.filter(student=student, status=3).exists()
#             if existing_choice:
#                 return Response({'message': '您已选择导师，请等待回复'}, status=status.HTTP_409_CONFLICT)
            
#             if not self.has_quota(professor, student):
#                 return Response({'message': '导师已没有名额'}, status=status.HTTP_400_BAD_REQUEST)

#             if student.postgraduate_type == 3:  # 博士
#                 # 检查博士招生专业 (ProfessorDoctorQuota.total_quota > 0)
#                 try:
#                     quota = ProfessorDoctorQuota.objects.get(
#                         professor=professor,
#                         subject=student.subject,
#                         remaining_quota__gt=0
#                     )
#                     StudentProfessorChoice.objects.create(
#                         student=student, 
#                         professor=professor, 
#                         status=3)
#                     # 考虑使用Django信号发送通知
#                     # 查询导师的openid
#                     # 尝试查询导师的微信账号，如果存在则发送通知
#                     try:
#                         professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
#                         professor_openid = professor_wechat_account.openid
#                         self.send_notification(professor_openid)  # 发送通知
#                     except WeChatAccount.DoesNotExist:
#                         # 如果导师的微信账号不存在，则不发送通知，但选择仍然成功
#                         pass
#                     return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)
#                 except ProfessorDoctorQuota.DoesNotExist:
#                     return Response({'message': '导师在您的专业下无招生名额'}, status=status.HTTP_401_UNAUTHORIZED)
#             else:
#                 # if student.subject in professor.enroll_subject.all():
#                 #     StudentProfessorChoice.objects.create(
#                 #         student=student, 
#                 #         professor=professor, 
#                 #         status=3)
#                 #     # 考虑使用Django信号发送通知
#                 #     # 查询导师的openid
#                 #     # 尝试查询导师的微信账号，如果存在则发送通知
#                 #     try:
#                 #         professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
#                 #         professor_openid = professor_wechat_account.openid
#                 #         self.send_notification(professor_openid)  # 发送通知
#                 #     except WeChatAccount.DoesNotExist:
#                 #         # 如果导师的微信账号不存在，则不发送通知，但选择仍然成功
#                 #         pass
#                 #     return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)
#                 # else:
#                 #     return Response({'message': '请选择在你的专业下招生的导师'}, status=status.HTTP_400_BAD_REQUEST)
#                 try:
#                     master_quota = ProfessorMasterQuota.objects.get(
#                         professor=professor,
#                         subject=student.subject
#                     )

#                     if student.postgraduate_type in [1, 2]:  # 北京专硕 or 学硕
#                         if master_quota.beijing_remaining_quota <= 0:
#                             return Response({'message': '导师在北京已无剩余名额'}, status=status.HTTP_400_BAD_REQUEST)
#                         # 扣减北京剩余名额
#                         master_quota.beijing_remaining_quota -= 1
#                         master_quota.save()

#                     elif student.postgraduate_type == 4:  # 烟台专硕
#                         if master_quota.yantai_remaining_quota <= 0:
#                             return Response({'message': '导师在烟台已无剩余名额'}, status=status.HTTP_400_BAD_REQUEST)
#                         # 扣减烟台剩余名额
#                         master_quota.yantai_remaining_quota -= 1
#                         master_quota.save()

#                     # 创建师生选择关系
#                     StudentProfessorChoice.objects.create(
#                         student=student,
#                         professor=professor,
#                         status=3
#                     )

#                     # 发送通知
#                     try:
#                         professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
#                         professor_openid = professor_wechat_account.openid
#                         self.send_notification(professor_openid)
#                     except WeChatAccount.DoesNotExist:
#                         pass  # 没有微信账号也不影响选择

#                     return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)

#                 except ProfessorMasterQuota.DoesNotExist:
#                     return Response({'message': '导师在您的专业下无招生名额'}, status=status.HTTP_401_UNAUTHORIZED)
#         except Professor.DoesNotExist:
#             # print("test")
#             return Response({'message': '导师不存在'}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             # 更通用的异常处理
#             return Response({'message': '服务器错误，请稍后再试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
#     def has_quota(self, professor, student):
#         # 这里需要实现逻辑来检查是否有足够的名额
#         # 示例逻辑，实际应用中可能会更复杂
#         if student.postgraduate_type == 1:  # 专业型(北京)
#             return professor.professional_quota > 0
#         elif student.postgraduate_type == 4:  # 专业型(烟台)
#             return professor.professional_yt_quota > 0
#         elif student.postgraduate_type == 2:  # 学术型
#             return professor.academic_quota > 0
#         elif student.postgraduate_type == 3:  # 博士
#             return professor.doctor_quota > 0
#         return False

#     def send_notification(self, professor_openid):
#         # 学生的openid和小程序的access_token
#         # access_token = cache.get('access_token')
#         # print(access_token)
#         # 微信小程序发送订阅消息的API endpoint
#         url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

#         # 构造消息数据
#         # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
#         data = {
#             "touser": professor_openid,
#             "template_id": "38wdqTPRI4y4eyGFrE1LrZy3o2CJB99oqehwfpv_AmE",  # 你在微信小程序后台设置的模板ID
#             "page": "index/selectinformation",  # 用户点击消息后跳转的小程序页面
#             "data": {
#                 "thing1": {"value": "有学生选择了您"},
#                 "time7": {"value": "2024-03-31"}
#             }
#         }

#         # 获取��前时间
#         current_time = datetime.now()

#         # 格式化时间为 YYYY-MM-DD HH:MM:SS 格式
#         formatted_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

#         # 将格式化后的时间设置为消息数据中的时间值
#         data["data"]["time7"]["value"] = formatted_time

#         # 发送POST请求
#         response = requests.post(url, json=data)
#         response_data = response.json()

#         # 检查请求是否成功
#         if response_data.get("errcode") == 0:
#             print("通知发送成功")
#         else:
#             print(f"通知发送失败: {response_data.get('errmsg')}")

class StudentChooseProfessorView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        is_open, selection_time = selection_time_is_open(SelectionTime.TARGET_STUDENT)
        if not selection_time:
            return Response({"message": "互选时间设置不存在"}, status=status.HTTP_404_NOT_FOUND)
        if not is_open:
            return Response({"message": "不在互选开放时间内"}, status=status.HTTP_400_BAD_REQUEST)

        student = request.user.student  # 假设 User 与 Student 是一对一关系

        # 🚫 新增逻辑：候补学生不能选导师
        if student.is_alternate:
            return Response(
                {"message": "您当前为候补状态，请等待系统补录"},
                status=status.HTTP_403_FORBIDDEN
            )

        # print(student)
        professor_id = request.data.get('professor_id')

        try:
            professor = Professor.objects.select_related('user_name').get(id=professor_id)

            # 学生已选导师检查
            if student.is_selected:
                return Response({'message': '您已完成导师选择'},
                                status=status.HTTP_405_METHOD_NOT_ALLOWED)

            existing_choice = StudentProfessorChoice.objects.filter(student=student, status=3).exists()
            if existing_choice:
                return Response({'message': '您已选择导师，请等待回复'}, status=status.HTTP_409_CONFLICT)

            source_type, quota_source = get_quota_source_for_student(professor, student, remaining_only=True)
            if not quota_source:
                if student.postgraduate_type == 3:
                    return Response({'message': '导师在您的博士专业下无招生名额'}, status=status.HTTP_401_UNAUTHORIZED)
                if student.postgraduate_type == 4:
                    return Response({'message': '导师在烟台已无剩余名额'}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'message': '导师在北京已无剩余名额'}, status=status.HTTP_400_BAD_REQUEST)

            StudentProfessorChoice.objects.create(
                student=student,
                professor=professor,
                status=3,
            )

            try:
                self._notify_professor(professor)
            except Exception as exc:
                logger.exception(
                    '学生选择导师后发送通知失败: professor_id=%s student_id=%s error=%s',
                    professor.id,
                    student.id,
                    exc,
                )
            return Response({'message': '选择成功，请等待回复'}, status=status.HTTP_201_CREATED)

        except Professor.DoesNotExist:
            return Response({'message': '导师不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': f'服务器错误，请稍后再试: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _notify_professor(self, professor):
        """
        发送微信通知
        """
        try:
            professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
            professor_openid = professor_wechat_account.openid
        except WeChatAccount.DoesNotExist:
            return  # 没有微信账号直接返回

        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'
        data = {
            "touser": professor_openid,
            "template_id": "38wdqTPRI4y4eyGFrE1LrZy3o2CJB99oqehwfpv_AmE",  # 替换为你的模板ID
            "page": "index/selectinformation",
            "data": {
                "thing1": {"value": "有学生选择了您"},
                "time7": {"value": timezone.now().strftime("%Y-%m-%d %H:%M:%S")}
            }
        }
        try:
            response = requests.post(url, json=data, timeout=10)
            response_data = response.json()
            if response_data.get("errcode") != 0:
                logger.warning("通知发送失败: %s", response_data.get('errmsg'))
        except Exception as exc:
            logger.exception("发送导师订阅通知失败: %s", exc)

# class ProfessorChooseStudentView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         professor = request.user.professor
#         student_id = request.data.get('student_id')
#         operation = request.data.get('operation')
        
#         try:
#             # 查询学生是否存在
#             student = Student.objects.get(id=student_id)

#             # 若学生已经完成导师选择
#             if student.is_selected:
#                 return Response({'message': '该学生已完成导师选择'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
            
#             latest_choice = StudentProfessorChoice.objects.filter(student=student, professor=professor).latest('submit_date')

#             # print(latest_choice)
#             if latest_choice.status != 3:  # 状态不是"请等待"
#                 return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_409_CONFLICT)
            
#             # 验证专业匹配
#             if student.postgraduate_type == 3:  # 博士
#                 try:
#                     quota = ProfessorDoctorQuota.objects.get(
#                         professor=professor,
#                         subject=student.subject,
#                         remaining_quota__gt=0
#                     )
#                     # 需要修改逻辑
#                 except ProfessorDoctorQuota.DoesNotExist:
#                     return Response(
#                         {'message': '学生报考专业不在您的博士招生专业中'},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
#             else:  # 硕士
#                 if student.subject not in professor.enroll_subject.all():
#                     return Response(
#                         {'message': '学生报考专业不在您的硕士招生专业中'},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )

#             if operation == '1':  # 同意请求
#                 if self.has_quota(professor, student):
#                     # 更新选择状态
#                     latest_choice.status = 1  # 同意请求
#                     latest_choice.chosen_by_professor = True
#                     latest_choice.finish_time = timezone.now()
#                     latest_choice.save()

#                     student.is_selected = True
#                     student.save()
#                     self.update_quota(professor, student)

#                     # print("done!")
#                     # 生成 PDF 并上传
#                     self.generate_and_upload_pdf(student, professor)

#                     self.send_notification(student, 'accepted')
#                     return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
#                 else:
#                     return Response({'message': '名额已满，无法选择更多学生'}, status=status.HTTP_403_FORBIDDEN)

#             elif operation == '2':  # 拒绝请求
#                 latest_choice.status = 2  # 拒绝请求
#                 latest_choice.finish_time = timezone.now()
#                 latest_choice.save()

#                 self.send_notification(student, 'rejected')
#                 return Response({'message': '操作成功'}, status=status.HTTP_200_OK)
#             else:
#                 return Response({'message': '操作不存在'}, status=status.HTTP_400_BAD_REQUEST)
#         except Student.DoesNotExist:
#             return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             return Response({'message': '服务器错，请稍后再试'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#     def generate_and_upload_pdf(self, student, professor):
#         """生成包含学生和导师信息的PDF，并上传到微信云托管"""
#         # 获取当前时间
#         date = timezone.now().strftime("%Y 年 %m 月 %d 日")
#         student_name = student.name
#         student_major = student.subject.subject_name
#         professor_name = professor.name

#         # 获取当前时间
#         now = datetime.now()

#         # 将当前时间转换为时间戳
#         timestamp = int(now.timestamp())

#         # 将时间戳转换为字符串
#         timestamp_str = str(timestamp)

#         # print(date)
#         # print(student_name)
#         # print(student_major)
#         # print(professor_name)

#         # 生成 PDF
#         packet = self.create_overlay(student_name, student_major, professor_name, date)

#         save_dir = '/app/Select_Information/tempFile/'
#         if not os.path.exists(save_dir):
#             os.makedirs(save_dir)
#         save_path = os.path.join(save_dir, f'{student.user_name.username}_{timestamp_str}_agreement.pdf')

#         print("sava_path: ", save_path)

#         # 将图层与现有的 PDF 模板合并
#         self.merge_pdfs(student, save_path, packet)

#         print("sava file")

#         # 上传到微信云托管
#         cloud_path = f"signature/student/{student.user_name.username}_{timestamp_str}_agreement.pdf"
#         self.upload_to_wechat_cloud(save_path, cloud_path, student)

#     def merge_pdfs(self, student, save_path, overlay_pdf):
#         """将生成的 PDF 图层与模板合并"""
#         if student.postgraduate_type == 3:
#             template_pdf_path = r'/app/Select_Information/pdfTemplate/template-phd.pdf'
#         else:
#             template_pdf_path = r'/app/Select_Information/pdfTemplate/template.pdf'
        
#         # 读取现有的 PDF 模板
#         template_pdf = PdfReader(template_pdf_path)
#         output = PdfWriter()

#         # 读取插入内容的 PDF
#         overlay_pdf = PdfReader(overlay_pdf)

#         # 合并两个 PDF
#         for i in range(len(template_pdf.pages)):
#             template_page = template_pdf.pages[i]
#             overlay_page = overlay_pdf.pages[i]

#             # 将插入内容叠加到模板上
#             template_page.merge_page(overlay_page)
#             output.add_page(template_page)

#         # 保存合并后的 PDF
#         with open(save_path, "wb") as output_stream:
#             output.write(output_stream)

#     def create_overlay(self, name, major, professor_name, date):
#         """生成 PDF 文件的动态内容"""
#         packet = io.BytesIO()
#         # print("done!")
#         can = canvas.Canvas(packet, pagesize=letter)

#         try:
#             # 注册支持中文的字体
#             pdfmetrics.registerFont(TTFont('simsun', r'/app/Select_Information/pdfTemplate/simsun.ttc'))
#             can.setFont('simsun', 12)
#         except Exception as e:
#             # 打印异常堆栈信息
#             print("Error occurred while registering the font:")
#             traceback.print_exc()

#         can.drawString(150, 683.5, name)
#         can.drawString(345, 683.5, major)
#         can.drawString(490, 638, professor_name)
#         # can.drawString(324, 497, date)

#         can.save()
#         packet.seek(0)
#         # print("done4")
#         return packet

#     def upload_to_wechat_cloud(self, save_path, cloud_path, student):
#         # 正常情况日志级别使用 INFO，需要定位时可以修改为 DEBUG，此时 SDK 会打印和服务端的通信信息
#         logging.basicConfig(level=logging.INFO, stream=sys.stdout)


#         # 1. 设置用户属性, 包括 secret_id, secret_key, region 等。Appid 已在CosConfig中移除，请在参数 Bucket 中带上 Appid。Bucket 由 BucketName-Appid 组成
#         secret_id = os.environ.get("COS_SECRET_ID")    # 用户的 SecretId，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
#         secret_key = os.environ.get("COS_SECRET_KEY")   # 用户的 SecretKey，建议使用子账号密钥，授权遵循最小权限指引，降低使用风险。子账号密钥获取可参见 https://cloud.tencent.com/document/product/598/37140
#         region = 'ap-shanghai'      # 替换为用户的 region，已创建桶归属的region可以在控制台查看，https://console.cloud.tencent.com/cos5/bucket
#                                 # COS 支持的所有 region 列表参见 https://cloud.tencent.com/document/product/436/6224
#         token = None               # 如果使用永久密钥不需要填入 token，如果使用临时密钥需要填入，临时密钥生成和使用指引参见 https://cloud.tencent.com/document/product/436/14048
#         scheme = 'https'           # 指定使用 http/https 协议来访问 COS，默认为 https，可不填


#         config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key, Token=token, Scheme=scheme)
#         client = CosS3Client(config)

#         print("upload file")

#         try:
#             url = f'https://api.weixin.qq.com/tcb/uploadfile'

#             data = {
#                 "env": 'prod-2g1jrmkk21c1d283',
#                 "path": cloud_path,
#             }

#             # 发送POST请求
#             response = requests.post(url, json=data)
#             response_data = response.json()
#             print(response_data)
#             # 自定义 metadata，包括 `x-cos-meta-fileid`
#             # metadata = {
#             #     "x-cos-meta-fileid": cloud_path
#             # }
#             # 根据文件大小自动选择简单上传或分块上传，分块上传具备断点续传功能。
#             response = client.upload_file(
#                 Bucket=os.environ.get("COS_BUCKET"),
#                 LocalFilePath=save_path,
#                 Key=cloud_path,
#                 PartSize=1,
#                 MAXThread=10,
#                 EnableMD5=False,
#                 Metadata={
#                     'x-cos-meta-fileid': response_data['cos_file_id']  # 自定义元数据
#                 }
#             )
#             print(f"文件上传成功: {response['ETag']}")
#             # print(f"文件上传成功: {response}")
#             # 上传成功后删除本地的临时文件
#             if os.path.exists(save_path):
#                 os.remove(save_path)
#                 print(f"本地临时文件已删除: {save_path}")
#             else:
#                 print(f"本地文件不存在: {save_path}")

#             # 上传成功后将路径保存到学生模型的 signature_table 字段
#             student.signature_table = response_data['file_id']
#             student.save()  # 保存更新后的学生信息
#             print(f"文件路径已保存到学生的 signature_table: {cloud_path}")

#         except Exception as e:
#             print(f"文件上传失败: {str(e)}")


#     def has_quota(self, professor, student):
#         # 封装可扩展的名额检查逻辑
#         quota_mapping = {
#             1: professor.professional_quota,
#             4: professor.professional_yt_quota,
#             2: professor.academic_quota,
#             3: professor.doctor_quota
#         }
#         return quota_mapping.get(student.postgraduate_type, 0) > 0

#     def update_quota(self, professor, student):
#         # # 这里需要实现逻辑来更新名额
#         # # 示例逻辑，实际应用中可能会更复杂
#         # if student.postgraduate_type == 1:  # 专业型(北京)
#         #     professor.professional_quota -= 1
#         # elif student.postgraduate_type == 4:  # 专业型(烟台)
#         #     professor.professional_yt_quota -= 1
#         # elif student.postgraduate_type == 2:  # "学术型"
#         #     professor.academic_quota -= 1
#         # elif student.postgraduate_type == 3:  # 博士
#         #     professor.doctor_quota -= 1
#         # professor.save()

        
#         if student.postgraduate_type == 3:  # 博士
#             try:
#                 quota = ProfessorDoctorQuota.objects.get(
#                     professor=professor,
#                     subject=student.subject
#                 )
#                 quota.used_quota += 1
#                 quota.save()  # 触发 Professor.save() 更新 doctor_quota
#             except ProfessorDoctorQuota.DoesNotExist:
#                 raise ValueError(f"No ProfessorDoctorQuota found for professor {professor.name} and subject {student.subject.subject_name}")
#         else:  # 硕士
#             quota_fields = {
#                 1: 'professional_quota',
#                 4: 'professional_yt_quota',
#                 2: 'academic_quota'
#             }
#             quota_field = quota_fields.get(student.postgraduate_type)
#             if quota_field:
#                 setattr(professor, quota_field, getattr(professor, quota_field) - 1)
#                 professor.save()

#     def send_notification(self, student, action):
#         # 学生的openid和小程序的access_token
#         try:
#             student_wechat_account = WeChatAccount.objects.get(user=student.user_name)
#             student_openid = student_wechat_account.openid
#             # access_token = cache.get('access_token')
#             if student_openid:
#                 # 微信小程序发送订阅消息的API endpoint
#                 url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

#                 # 构造消息数据
#                 # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
#                 data = {
#                     "touser": student_openid,
#                     "template_id": "S1D5wX7_WY5BIfZqw0dEnyoYjjAtNPmz9QlfApZ9uOs",  # 你在微信小程序后台设置的模板ID
#                     "page": "index/selectinformation",  # 用户点击消息后跳转的小程序页面
#                     "data": {
#                         "phrase5": {"value": "审核结果"},
#                         "date7": {"value": timezone.now().strftime("%Y-%m-%d")}
#                     }
#                 }
#                 # 对于不同的操作，发送不同的消息
#                 if action == "accepted":
#                     data["data"]["phrase5"]["value"] = "接受"
#                 elif action == "rejected":
#                     data["data"]["phrase5"]["value"] = "拒绝"

#             # 发送POST请求
#             response = requests.post(url, json=data)
#             response_data = response.json()

#             # 检查请求是否成功
#             if response_data.get("errcode") == 0:
#                 print("通知发送成功")
#             else:
#                 print(f"通知发送失败: {response_data.get('errmsg')}")
#         except WeChatAccount.DoesNotExist:
#             # 如果学生没有绑定微信账号信息，则不发送通知
#             print("学生微信账号不存在，无法发送通知。")

class ProfessorChooseStudentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        is_open, selection_time = selection_time_is_open(SelectionTime.TARGET_PROFESSOR)
        if not selection_time:
            return Response({'message': '当前未设置导师处理学生时间，请联系管理员配置。'}, status=status.HTTP_404_NOT_FOUND)
        if not is_open:
            return Response(
                {
                    'message': format_selection_time_window(selection_time, '导师处理学生'),
                    'open_time': timezone.localtime(selection_time.open_time).isoformat(),
                    'close_time': timezone.localtime(selection_time.close_time).isoformat(),
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        professor = request.user.professor
        student_id = request.data.get('student_id')
        operation = request.data.get('operation')

        try:
            student = Student.objects.get(id=student_id)

            # 学生已完成选择
            if student.is_selected:
                return Response({'message': '该学生已完成导师选择'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

            latest_choice = StudentProfessorChoice.objects.filter(
                student=student, professor=professor
            ).latest('submit_date')

            if latest_choice.status != 3:  # 3 = 等待导师确认
                return Response({'message': '不存在等待审核的记录'}, status=status.HTTP_409_CONFLICT)

            source_type, quota_source = get_quota_source_for_student(professor, student, remaining_only=False)
            if not quota_source:
                if student.postgraduate_type == 3:
                    return Response({'message': '学生报考专业不在您的博士招生专业中'}, status=status.HTTP_400_BAD_REQUEST)
                return Response({'message': '学生报考专业不在您的硕士招生专业中'}, status=status.HTTP_400_BAD_REQUEST)

            # 处理操作
            if operation == '1':  # ✅ 接受
                if self.has_quota(professor, student):
                    # 更新选择记录
                    latest_choice.status = 1
                    latest_choice.chosen_by_professor = True
                    latest_choice.finish_time = timezone.now()
                    latest_choice.shared_quota_pool = quota_source if source_type == 'shared' else None

                    # 扣减名额
                    self.update_quota(professor, student, latest_choice)

                    latest_choice.save(update_fields=['status', 'chosen_by_professor', 'finish_time', 'shared_quota_pool'])

                    # 学生标记为已选择
                    student.is_selected = True
                    student.save(update_fields=['is_selected'])

                    # 🔑 检查名额是否为 0，如果为 0，则拒绝所有等待中的申请
                    self.reject_waiting_choices_if_quota_full(professor, student, latest_choice)

                    # 生成 PDF、上传文件、发送通知属于附加动作，失败时不影响互选主流程
                    try:
                        self.generate_and_upload_pdf(student, professor)
                    except Exception as exc:
                        logger.exception(
                            '导师接受学生后生成/上传互选材料失败: professor_id=%s student_id=%s error=%s',
                            professor.id,
                            student.id,
                            exc,
                        )

                    try:
                        self.send_notification(student, 'accepted')
                    except Exception as exc:
                        logger.exception(
                            '导师接受学生后发送通知失败: professor_id=%s student_id=%s error=%s',
                            professor.id,
                            student.id,
                            exc,
                        )
                    return Response({'message': '操作成功'}, status=status.HTTP_202_ACCEPTED)
                else:
                    return Response({'message': '名额已满，无法选择更多学生'}, status=status.HTTP_403_FORBIDDEN)

            elif operation == '2':  # ❌ 拒绝
                latest_choice.status = 2
                latest_choice.finish_time = timezone.now()
                latest_choice.save()

                try:
                    self.send_notification(student, 'rejected')
                except Exception as exc:
                    logger.exception(
                        '导师拒绝学生后发送通知失败: professor_id=%s student_id=%s error=%s',
                        professor.id,
                        student.id,
                        exc,
                    )
                return Response({'message': '操作成功'}, status=status.HTTP_200_OK)

            else:
                return Response({'message': '操作不存在'}, status=status.HTTP_400_BAD_REQUEST)

        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': f'服务器错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def reject_waiting_choices_if_quota_full(self, professor, student, choice=None):
        """
        如果该专业名额为 0，则自动拒绝该导师在该专业下所有等待处理的申请
        """
        if choice and choice.shared_quota_pool_id:
            shared_pool = choice.shared_quota_pool
            if shared_pool and shared_pool.remaining_quota <= 0:
                subject_ids = list(shared_pool.subjects.values_list('id', flat=True))
                waiting_choices = StudentProfessorChoice.objects.filter(
                    professor=professor,
                    student__subject_id__in=subject_ids,
                    status=3,
                )
                if shared_pool.quota_scope == 'doctor':
                    waiting_choices = waiting_choices.filter(student__postgraduate_type=3)
                elif shared_pool.campus == 'beijing':
                    waiting_choices = waiting_choices.filter(student__postgraduate_type__in=[1, 2])
                elif shared_pool.campus == 'yantai':
                    waiting_choices = waiting_choices.filter(student__postgraduate_type=4)

                for waiting_choice in waiting_choices:
                    waiting_choice.status = 2
                    waiting_choice.finish_time = timezone.now()
                    waiting_choice.save(update_fields=['status', 'finish_time'])
                    self.send_notification(waiting_choice.student, 'rejected')
            return

        if student.postgraduate_type == 3:  # 博士
            quota = ProfessorDoctorQuota.objects.filter(professor=professor, subject=student.subject).first()
            if quota and quota.remaining_quota <= 0:
                waiting_choices = StudentProfessorChoice.objects.filter(
                    professor=professor, student__subject=student.subject, status=3
                )
                for choice in waiting_choices:
                    choice.status = 2  # 拒绝
                    choice.finish_time = timezone.now()
                    choice.save()
                    self.send_notification(choice.student, 'rejected')

        else:  # 硕士
            quota = ProfessorMasterQuota.objects.filter(professor=professor, subject=student.subject).first()
            if quota:
                # 判断名额是否为 0
                if (student.postgraduate_type in [1, 2] and quota.beijing_remaining_quota <= 0) or \
                   (student.postgraduate_type == 4 and quota.yantai_remaining_quota <= 0):

                    waiting_choices = StudentProfessorChoice.objects.filter(
                        professor=professor, student__subject=student.subject, status=3
                    )
                    for choice in waiting_choices:
                        choice.status = 2  # 拒绝
                        choice.finish_time = timezone.now()
                        choice.save()
                        self.send_notification(choice.student, 'rejected')

    # ================= 名额检查 =================
    def has_quota(self, professor, student):
        _, quota_source = get_quota_source_for_student(professor, student, remaining_only=True)
        return quota_source is not None

    # ================= 扣减名额 =================
    def update_quota(self, professor, student, choice=None):
        source_type, quota_source = get_quota_source_for_student(professor, student, remaining_only=True)
        if not quota_source:
            raise ValueError('没有可用名额')

        if source_type == 'shared':
            quota_source.remaining_quota -= 1
            quota_source.used_quota += 1
            quota_source.save(update_fields=["remaining_quota", "used_quota", "updated_at"])
            recalculate_professor_quota_summary(professor)
            return

        if student.postgraduate_type == 3:
            quota_source.remaining_quota -= 1
            quota_source.used_quota += 1
            quota_source.save(update_fields=["remaining_quota", "used_quota"])
            recalculate_professor_quota_summary(professor)
            return

        if student.postgraduate_type in [1, 2]:
            quota_source.beijing_remaining_quota -= 1
        elif student.postgraduate_type == 4:
            quota_source.yantai_remaining_quota -= 1
        quota_source.save(update_fields=["beijing_remaining_quota", "yantai_remaining_quota"])
        recalculate_professor_quota_summary(professor)

    # ================= PDF 生成 & 上传 =================
    def generate_and_upload_pdf(self, student, professor):
        logger.info('开始生成并上传互选材料: student_id=%s professor_id=%s', student.id, professor.id)

        date = timezone.now().strftime("%Y 年 %m 月 %d 日")
        student_name = student.name
        student_major = student.subject.subject_name
        professor_name = professor.name

        now = datetime.now()
        timestamp_str = str(int(now.timestamp()))

        packet = self.create_overlay(student_name, student_major, professor_name, date)

        save_dir = '/app/Select_Information/tempFile/'
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, f'{student.user_name.username}_{timestamp_str}_agreement.pdf')

        self.merge_pdfs(student, save_path, packet)

        cloud_path = f"signature/student/{student.user_name.username}_{timestamp_str}_agreement.pdf"
        self.upload_to_wechat_cloud(save_path, cloud_path, student)

    def merge_pdfs(self, student, save_path, overlay_pdf):
        template_pdf_path = (
            r'/app/Select_Information/pdfTemplate/template-phd.pdf'
            if student.postgraduate_type == 3
            else r'/app/Select_Information/pdfTemplate/template.pdf'
        )
        template_pdf = PdfReader(template_pdf_path)
        output = PdfWriter()
        overlay_pdf = PdfReader(overlay_pdf)

        for i in range(len(template_pdf.pages)):
            template_page = template_pdf.pages[i]
            overlay_page = overlay_pdf.pages[i]
            template_page.merge_page(overlay_page)
            output.add_page(template_page)

        with open(save_path, "wb") as output_stream:
            output.write(output_stream)

    def create_overlay(self, name, major, professor_name, date):
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        try:
            pdfmetrics.registerFont(TTFont('simsun', r'/app/Select_Information/pdfTemplate/simsun.ttc'))
            can.setFont('simsun', 12)
        except Exception:
            traceback.print_exc()

        can.drawString(150, 683.5, name)
        can.drawString(345, 683.5, major)
        can.drawString(490, 638, professor_name)
        can.save()
        packet.seek(0)
        return packet

    def upload_to_wechat_cloud(self, save_path, cloud_path, student):
        bucket = os.environ.get('COS_BUCKET')
        secret_id = os.environ.get('COS_SECRET_ID')
        secret_key = os.environ.get('COS_SECRET_KEY')

        logger.info(
            '准备上传互选材料: save_path=%s cloud_path=%s has_secret_id=%s has_secret_key=%s has_bucket=%s',
            save_path,
            cloud_path,
            bool(secret_id),
            bool(secret_key),
            bool(bucket),
        )

        try:
            if not secret_id or not secret_key:
                logger.warning('未配置 COS_SECRET_ID 或 COS_SECRET_KEY，跳过互选材料上传。')
                return
            if not bucket:
                logger.warning('未配置 COS_BUCKET，跳过互选材料上传。')
                return

            region = 'ap-shanghai'
            config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
            client = CosS3Client(config)

            access_token = get_wechat_access_token()
            url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'
            data = {"env": WECHAT_CLOUD_ENV, "path": cloud_path}
            response = requests.post(url, json=data, timeout=15)
            response.raise_for_status()
            response_data = response.json()

            if response_data.get('errcode') not in (None, 0):
                errcode = response_data.get('errcode')
                if errcode == 41001:
                    access_token = get_wechat_access_token(force_refresh=True)
                    refresh_url = f'https://api.weixin.qq.com/tcb/uploadfile?access_token={access_token}'
                    response = requests.post(refresh_url, json=data, timeout=15)
                    response.raise_for_status()
                    response_data = response.json()
                if response_data.get('errcode') not in (None, 0):
                    raise ValueError(response_data.get('errmsg') or '调用 tcb/uploadfile 失败。')

            cos_file_id = response_data.get('cos_file_id')
            if not cos_file_id:
                raise ValueError('微信接口未返回 cos_file_id，无法写入 x-cos-meta-fileid。')

            client.upload_file(
                Bucket=bucket,
                LocalFilePath=save_path,
                Key=cloud_path,
                PartSize=1,
                MAXThread=10,
                EnableMD5=False,
                Metadata={'x-cos-meta-fileid': cos_file_id}
            )

            file_id = response_data.get('file_id')
            if not file_id:
                file_id = f'cloud://{WECHAT_CLOUD_ENV}.{bucket}/{cloud_path}'
                logger.warning('微信接口未返回 file_id，使用推导值回填: %s', file_id)

            student.signature_table = file_id
            student.save()
            logger.info('互选材料上传成功并已写入 signature_table: student_id=%s file_id=%s', student.id, file_id)
        except Exception as e:
            logger.exception('文件上传失败: %s', e)
        finally:
            if os.path.exists(save_path):
                try:
                    os.remove(save_path)
                except Exception:
                    logger.exception('删除本地临时文件失败: %s', save_path)

    # ================= 通知学生 =================
    def send_notification(self, student, action):
        try:
            student_wechat_account = WeChatAccount.objects.get(user=student.user_name)
            student_openid = student_wechat_account.openid
            if not student_openid:
                return

            url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'
            data = {
                "touser": student_openid,
                "template_id": "S1D5wX7_WY5BIfZqw0dEnyoYjjAtNPmz9QlfApZ9uOs",
                "page": "index/selectinformation",
                "data": {
                    "phrase5": {"value": "接受" if action == "accepted" else "拒绝"},
                    "date7": {"value": timezone.now().strftime("%Y-%m-%d")}
                }
            }
            response = requests.post(url, json=data)
            response_data = response.json()
            if response_data.get("errcode") != 0:
                logger.warning("通知发送失败: %s", response_data.get('errmsg'))
        except WeChatAccount.DoesNotExist:
            logger.warning("学生微信账号不存在，无法发送通知。")
        except Exception as exc:
            logger.exception("发送订阅通知失败: %s", exc)


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
                return Response({'message': '双方未完成签署'}, status=status.HTTP_400_BAD_REQUEST)

            # 已同意不能提交
            if student.signature_table_review_status == True:
                return Response({'message': '已通过审核！'}, status=status.HTTP_400_BAD_REQUEST)


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
                    return Response({'message': '已通过审核！'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    return Response({'message': '请勿重复提交'}, status=status.HTTP_400_BAD_REQUEST)

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
            self.notify_department_reviewer(professor, review_professor)

            return Response({'message': '提交审核成功'}, status=status.HTTP_200_OK)
        except Student.DoesNotExist:
            return Response({'message': '学生不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'message': f'服务器错误: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def notify_department_reviewer(self, professor, review_professor):
        # 学生的openid和小程序的access_token
        try:
            professor_wechat_account = WeChatAccount.objects.get(user=review_professor.user_name)
            professor_openid = professor_wechat_account.openid

            professor_name = professor.name
            translation_table = str.maketrans('', '', '0123456789')
            cleaned_name = professor_name.translate(translation_table)
            # print(type(professor_name))
            # print("professor_openid: ", professor_openid)
            # access_token = cache.get('access_token')
            if professor_openid:
                # 微信小程序发送订阅消息的API endpoint
                url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

                # 构造消息数据
                # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
                data = {
                    "touser": professor_openid,
                    "template_id": "viilL7yUx1leDVAsGCsrBEkQS9v7A9NT6yH90MFP3jg",  # 你在微信小程序后台设置的模板ID
                    "page": "pages/profile/profile",  # 用户点击消息后跳转的小程序页面
                    "data": {
                        "short_thing23": {"value": "意向表审核"},
                        "name1": {"value": cleaned_name},
                        "time19": {"value": timezone.now().strftime('%Y年%m月%d日 %H:%M')}
                    }
                }
            print("data: ", data)

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
            print("导师微信账号不存在，无法发送通知。")


class ReviewerReviewRecordsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        reviewer = request.user.professor
        page = SelectInformationView._safe_int(request.query_params.get('page', 1), 1, 1, 99999)
        page_size = SelectInformationView._safe_int(request.query_params.get('page_size', 10), 10, 1, 50)
        review_status = SelectInformationView._safe_int(request.query_params.get('review_status', 0), 0, 0, 3)

        review_records_queryset = ReviewRecord.objects.select_related(
            'student', 'professor', 'professor__department', 'reviewer'
        ).filter(reviewer=reviewer).order_by('-submit_time', '-id')

        counts = {
            'pending': review_records_queryset.filter(review_status=False).count(),
            'approved': review_records_queryset.filter(review_status=True, status=1).count(),
            'rejected': review_records_queryset.filter(review_status=True, status=2).count(),
        }

        if review_status == 1:
            review_records_queryset = review_records_queryset.filter(review_status=False)
        elif review_status == 2:
            review_records_queryset = review_records_queryset.filter(review_status=True, status=1)
        elif review_status == 3:
            review_records_queryset = review_records_queryset.filter(review_status=True, status=2)

        paginator = Paginator(review_records_queryset, page_size)
        try:
            review_records_page = paginator.page(page)
        except:
            review_records_page = paginator.page(1)

        serializer = ReviewRecordSerializer(review_records_page, many=True)
        return Response({
            'results': serializer.data,
            'counts': counts,
            'has_next': review_records_page.has_next(),
            'has_previous': review_records_page.has_previous(),
            'page': review_records_page.number,
            'page_size': page_size,
            'total_pages': paginator.num_pages,
            'total_count': paginator.count,
            'review_status': review_status,
        }, status=status.HTTP_200_OK)
    
class ReviewRecordUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review_record = ReviewRecord.objects.get(pk=pk, reviewer=request.user.professor)
            # print("request.data: ", request.data)
            review_status = request.data['status']
            professor = review_record.professor
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

                # 通知导师审核完成
                self.notify_department_reviewer(professor, 1)
                return Response({'message': '审核成功'}, status=status.HTTP_200_OK)
            else:
                serializer.save(review_time=timezone.now())
                student = review_record.student
                student.signature_table_review_status = 2
                student.save()

                # 通知导师审核完成
                self.notify_department_reviewer(professor, 2)
                return Response({'message': '审核成功'}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def notify_department_reviewer(self, professor, status):
        try:
            professor_wechat_account = WeChatAccount.objects.get(user=professor.user_name)
            professor_openid = professor_wechat_account.openid

            if status == 1:
                status_str = "通过"
            else:
                status_str = "拒绝"
            # professor_name = professor.name
            # translation_table = str.maketrans('', '', '0123456789')
            # cleaned_name = professor_name.translate(translation_table)
            # print(type(professor_name))
            # print("professor_openid: ", professor_openid)
            # access_token = cache.get('access_token')
            if professor_openid:
                # 微信小程序发送订阅消息的API endpoint
                url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send'

                # 构造消息数据
                # 注意：这里的key（如phrase1, time11等）和template_id需要根据你在微信后台配置的模板来确定
                data = {
                    "touser": professor_openid,
                    "template_id": "S1D5wX7_WY5BIfZqw0dEn4MTL-FPvlNBKiHPAAQngx0",  # 你在微信小程序后台设置的模板ID
                    "page": "pages/profile/profile",  # 用户点击消息后跳转的小程序页面
                    "data": {
                        "thing23": {"value": "意向表审核"},
                        "phrase5": {"value": status_str},
                        "date7": {"value": timezone.now().strftime('%Y年%m月%d日 %H:%M')}
                    }
                }
            # print("data: ", data)

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
            print("导师微信账号不存在，无法发送通知。")


