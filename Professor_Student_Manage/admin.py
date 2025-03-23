from django.contrib import admin
from django import forms
from django.utils.html import format_html
import requests
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render, redirect
from django.urls import path
import csv
from io import TextIOWrapper

# Register your models here.
from .models import Student, Professor, WeChatAccount


@admin.action(description="重置导师指定类型的名额")
def reset_quota(modeladmin, request, queryset):
    # 获取用户选择的类型
    quota_type = request.POST.get('quota_type')

    # 根据类型重置名额
    if quota_type == 'academic':
        queryset.update(academic_quota=0)
    elif quota_type == 'professional':
        queryset.update(professional_quota=0)
    elif quota_type == 'professional_yt':
        queryset.update(professional_yt_quota=0)
    elif quota_type == 'doctor':
        queryset.update(doctor_quota=0)
    else:
        modeladmin.message_user(request, "请选择有效的名额类型", level='error')
        return

    modeladmin.message_user(request, f"已成功重置 {queryset.count()} 位导师的 {quota_type} 名额为 0")


@admin.action(description="重置导师状态为未开放选择: ")
def reset_proposed_quota_approved(modeladmin, request, queryset):
    # 将选中的导师的 proposed_quota_approved 字段重置为 False
    queryset.update(proposed_quota_approved=False)
    modeladmin.message_user(request, f"已成功重置 {queryset.count()} 位导师的“设置指标”为 False")


# 文件上传表单
class ImportQuotaForm(forms.Form):
    csv_file = forms.FileField(label="选择 CSV 文件")


class ProfessorAdmin(admin.ModelAdmin):
    fieldsets = [
        ("导师信息更改", {"fields": ["name", "teacher_identity_id", "email", "department", "enroll_subject",
                                     "academic_quota", "professional_quota", "professional_yt_quota", "doctor_quota", "proposed_quota_approved",
                                     "have_qualification", "remaining_quota", "personal_page", "research_areas",
                                     "avatar", "contact_details", "department_position"]}),
    ]
    list_display = ["teacher_identity_id", "name", "department", "have_qualification", "proposed_quota_approved"]
    readonly_fields = ["remaining_quota"]
    actions = [reset_quota, reset_proposed_quota_approved]
    change_list_template = 'admin/professor_change_list.html'  # 自定义列表页面模板


    def get_actions(self, request):
        actions = super().get_actions(request)
        # 添加自定义动作选项
        actions['reset_academic_quota'] = (
            reset_quota,
            'reset_academic_quota',
            '重置学硕名额为 0'
        )
        actions['reset_professional_quota'] = (
            reset_quota,
            'reset_professional_quota',
            '重置北京专硕名额为 0'
        )
        actions['reset_professional_yt_quota'] = (
            reset_quota,
            'reset_professional_yt_quota',
            '重置烟台专硕名额为 0'
        )
        actions['reset_doctor_quota'] = (
            reset_quota,
            'reset_doctor_quota',
            '重置博士名额为 0'
        )
        actions['reset_proposed_quota_approved'] = (
            reset_proposed_quota_approved,
            'reset_proposed_quota_approved',
            '重置所选导师状态为未开放选择'
        )
        return actions

    def response_action(self, request, queryset):
        # 获取用户选择的动作
        action = request.POST.get('action')
        if action in ['reset_academic_quota', 'reset_professional_quota', 'reset_professional_yt_quota', 'reset_doctor_quota']:
            # 设置 quota_type
            quota_type = action.split('_')[1]  # 从动作名称中提取类型
            request.POST = request.POST.copy()  # 使 POST 数据可变
            request.POST['quota_type'] = quota_type
        return super().response_action(request, queryset)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-quota/', self.admin_site.admin_view(self.import_quota_view), name='import_quota'),
        ]
        return custom_urls + urls

    def import_quota_view(self, request):
        if request.method == 'POST':
            form = ImportQuotaForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                try:
                    # 读取 CSV 文件
                    csv_file_wrapper = TextIOWrapper(csv_file, encoding='utf-8-sig')
                    reader = csv.DictReader(csv_file_wrapper)
                    # print("reader.fieldnames: ", reader.fieldnames)
                    # 检查列名是否正确
                    required_columns = ["工号", "姓名", "学术学位硕士", "专硕北京", "专硕烟台", "博士"]
                    if not all(column in reader.fieldnames for column in required_columns):
                        self.message_user(request, "CSV 文件列名不正确，请确保包含：工号、姓名、学术学位硕士、专硕北京、专硕烟台、博士", level='error')
                        return redirect('admin:Professor_Student_Manage_professor_changelist')

                    # 更新导师名额
                    success_count = 0
                    for row in reader:
                        teacher_identity_id = row["工号"]
                        try:
                            professor = Professor.objects.get(teacher_identity_id=teacher_identity_id)
                            professor.academic_quota = int(row["学术学位硕士"])
                            professor.professional_quota = int(row["专硕北京"])
                            professor.professional_yt_quota = int(row["专硕烟台"])
                            professor.doctor_quota = int(row["博士"])
                            professor.save()
                            success_count += 1
                        except Professor.DoesNotExist:
                            self.message_user(request, f"工号 {teacher_identity_id} 对应的导师不存在", level='warning')
                            continue
                        except ValueError:
                            self.message_user(request, f"工号 {teacher_identity_id} 的名额数据格式不正确", level='warning')
                            continue

                    self.message_user(request, f"成功更新 {success_count} 位导师的名额信息")
                    return redirect('admin:Professor_Student_Manage_professor_changelist')
                except Exception as e:
                    self.message_user(request, f"解析 CSV 文件时出错: {str(e)}", level='error')
                    return redirect('admin:Professor_Student_Manage_professor_changelist')
        else:
            form = ImportQuotaForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'title': '一键导入导师名额',
        }
        return render(request, 'admin/import_quota.html', context)

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
                "<a href='{}' download>下载</a>", signature_download_url
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
                "<a href='{}' download>下载</a>", signature_download_url
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
    download_fq_file.short_description = "弃选表下载"


class WeChatAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "openid", "session_key"]


admin.site.register(Student, StudentAdmin)
admin.site.register(Professor, ProfessorAdmin)
admin.site.register(WeChatAccount, WeChatAccountAdmin)


