from django.contrib import admin
from django import forms
from django.utils.html import format_html
import requests
from rest_framework.response import Response
from rest_framework import status

# Register your models here.
from .models import Student, Professor, WeChatAccount


class ProfessorAdmin(admin.ModelAdmin):
    fieldsets = [
        ("导师信息更改", {"fields": ["name", "teacher_identity_id", "email", "department", "enroll_subject",
                                     "academic_quota", "professional_quota", "professional_yt_quota", "doctor_quota", "proposed_quota_approved",
                                     "have_qualification", "remaining_quota", "personal_page", "research_areas",
                                     "avatar", "contact_details", "department_position"]}),
    ]
    list_display = ["teacher_identity_id", "name", "department", "have_qualification", "proposed_quota_approved"]
    readonly_fields = ["remaining_quota"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = self.readonly_fields
        if obj and obj.proposed_quota_approved == True:  # 根据字段值来判断是否设置为只读
            readonly_fields = ["academic_quota", "professional_quota", "professional_yt_quota", "doctor_quota",
                               "have_qualification", "remaining_quota"]
        return readonly_fields

    list_filter = ["department_id", "proposed_quota_approved", "have_qualification"]
    search_fields = ["name"]


class StudentAdmin(admin.ModelAdmin):
    # fieldsets 元组中的第一个元素是字段集的标题
    fieldsets = [
        ("学生信息更改", {"fields": ["name", "candidate_number", "student_type", "subject", 
                               "postgraduate_type", "study_mode", "resume", "avatar", "phone_number",
                               "initial_exam_score", "initial_rank", "secondary_exam_score",
                               "secondary_rank", "final_rank", "is_selected", "is_giveup"]}),
    ]
    list_display = ["candidate_number", "name", "subject", "study_mode", "student_type", "postgraduate_type", "is_selected", "is_giveup", "download_hx_file", "download_fq_file"]
    list_filter = ["subject"]
    search_fields = ["name"]

    def download_fq_file(self, obj):
        """
        若学生已放弃拟录取并且 hx_file 有文件，则显示下载链接；否则显示 '-'
        """
        if obj.is_giveup == True:

            # 获取下载地址
            response_data_signature = self.get_fileid_download_url(obj.giveup_signature_table)
            if response_data_signature.get("errcode") == 0:
                signature_download_url = response_data_signature['file_list'][0]['download_url']
                print(f"放弃说明表下载地址: {signature_download_url}")
            else:
                return Response({'message': '获取放弃说明表下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return format_html(
                "<a href='{}' download>下载互选表</a>", signature_download_url
            )
        return '未完成'

    def download_hx_file(self, obj):
        """
        若学生已放弃拟录取并且 hx_file 有文件，则显示下载链接；否则显示 '-'
        """
        if obj.is_selected == True and obj.signature_table_review_status == 1:

            # 获取下载地址
            response_data_signature = self.get_fileid_download_url(obj.signature_table)
            if response_data_signature.get("errcode") == 0:
                signature_download_url = response_data_signature['file_list'][0]['download_url']
                print(f"签名图片下载地址: {signature_download_url}")
            else:
                return Response({'message': '获取签名图片下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            return format_html(
                "<a href='{}' download>下载互选表</a>", signature_download_url
            )
        return '未完成'

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

    download_hx_file.short_description = "互选表下载"
    download_fq_file.short_description = "放弃表下载"


class WeChatAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "openid", "session_key"]


admin.site.register(Student, StudentAdmin)
admin.site.register(Professor, ProfessorAdmin)
admin.site.register(WeChatAccount, WeChatAccountAdmin)


