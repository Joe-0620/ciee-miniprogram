# Professor_Student_Manage/admin.py
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
from django.contrib.auth.models import User

# Register your models here.
from .models import Student, Professor, WeChatAccount, ProfessorDoctorQuota, ProfessorMasterQuota
from Enrollment_Manage.models import Subject
from django.http import JsonResponse

class ProfessorDoctorQuotaInline(admin.TabularInline):
    model = ProfessorDoctorQuota
    extra = 0  # 不显示额外的空行
    fields = ['subject', 'total_quota', 'used_quota', 'remaining_quota']
    readonly_fields = ['used_quota', 'remaining_quota']  # 已用和剩余名额只读
    can_delete = False  # 禁止删除，确保每个博士专业都有记录

@admin.register(ProfessorDoctorQuota)
class ProfessorDoctorQuotaAdmin(admin.ModelAdmin):
    list_display = ['professor', 'subject', 'total_quota', 'used_quota', 'remaining_quota']
    list_filter = ['professor', 'subject']
    search_fields = ['professor__name', 'subject__subject_name']

# ========= 新增硕士专业内联 =========
class ProfessorMasterQuotaInline(admin.TabularInline):
    model = ProfessorMasterQuota
    extra = 0
    fields = ['subject', 'beijing_quota', 'beijing_remaining_quota',
              'yantai_quota', 'yantai_remaining_quota', 'total_quota']
    readonly_fields = ['beijing_remaining_quota', 'yantai_remaining_quota', 'total_quota']
    can_delete = False

@admin.register(ProfessorMasterQuota)
class ProfessorMasterQuotaAdmin(admin.ModelAdmin):
    list_display = ['professor', 'subject', 'beijing_quota', 'beijing_remaining_quota',
                    'yantai_quota', 'yantai_remaining_quota', 'total_quota']
    list_filter = ['professor', 'subject']
    search_fields = ['professor__name', 'subject__subject_name']
    readonly_fields = ['beijing_remaining_quota', 'yantai_remaining_quota', 'total_quota']


@admin.action(description="重置导师指定类型的名额")
def reset_quota(modeladmin, request, queryset):
    # 获取用户选择的类型
    quota_type = request.POST.get('quota_type')

    # 根据类型重置名额
    if quota_type == 'academic':
        queryset.update(academic_quota=0)
    elif quota_type == 'professional':
        queryset.update(professional_quota=0)
    elif quota_type == 'professionalyt':
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
        ("导师信息更改", {"fields": ["name", "teacher_identity_id", "professor_title", "email", "department", "enroll_subject",
                                     "academic_quota", "professional_quota", "professional_yt_quota", "doctor_quota", "proposed_quota_approved",
                                     "have_qualification", "remaining_quota", "personal_page", "research_areas",
                                     "avatar", "contact_details", "department_position"]}),
    ]
    list_display = ["teacher_identity_id", "name", "department", "have_qualification", "proposed_quota_approved"]
    readonly_fields = ["remaining_quota"]
    actions = [reset_quota, reset_proposed_quota_approved, 'reset_password_to_teacher_id']
    change_list_template = 'admin/professor_change_list.html'  # 自定义列表页面模板
    inlines = [ProfessorMasterQuotaInline, ProfessorDoctorQuotaInline]  # 内联显示硕士、博士专业名额

    def reset_password_to_teacher_id(self, request, queryset):
        """
        将选中导师的密码重置为工号（teacher_identity_id）
        """
        for professor in queryset:
            if professor.user_name:  # 确保关联的 User 对象存在
                teacher_id = professor.teacher_identity_id
                professor.user_name.set_password(teacher_id)  # 重置密码
                professor.user_name.save()
                self.message_user(
                    request,
                    f"已重置导师 {professor.name} 的密码为工号: {teacher_id}",
                    level='success'
                )
    reset_password_to_teacher_id.short_description = "重置密码为工号"  # 动作显示名称

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
        actions['reset_professionalyt_quota'] = (
            reset_quota,
            'reset_professionalyt_quota',
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
        if action in ['reset_academic_quota', 'reset_professional_quota', 'reset_professionalyt_quota', 'reset_doctor_quota']:
            # 设置 quota_type
            print("action: ", action)
            quota_type = action.split('_')[1]  # 从动作名称中提取类型
            print("quota_type: ", quota_type)
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
                        print(row)
                        teacher_identity_id = row["工号"]
                        teacher_identity_id = str(teacher_identity_id).zfill(5)
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
            # readonly_fields = ["academic_quota", "professional_quota", "professional_yt_quota", "doctor_quota",
            #                    "have_qualification", "remaining_quota"]
            readonly_fields = ["have_qualification", "remaining_quota"]
        return readonly_fields

    list_filter = ["department_id", "proposed_quota_approved", "have_qualification"]
    search_fields = ["name"]


class ImportStudentForm(forms.Form):
    csv_file = forms.FileField(label="选择 CSV 文件")


class CustomModelChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        # 自定义下拉菜单选项显示为：专业名称 (专业类别)
        return f"{obj.subject_name} ({obj.get_subject_type_display()})"


class StudentAdmin(admin.ModelAdmin):
    # fieldsets 元组中的第一个元素是字段集的标题
    fieldsets = [
        ("学生信息更改", {"fields": ["name", "candidate_number", "student_type", "subject", 
                               "postgraduate_type", "study_mode", "resume", "avatar", "phone_number",
                               "initial_exam_score", "initial_rank", "secondary_exam_score",
                               "secondary_rank", "final_rank", "signature_table_student_signatured", 
                               "signature_table_professor_signatured", "signature_table_review_status", 
                               "is_selected", "is_giveup", "is_alternate"]}),
    ]
    list_display = ["candidate_number", "name", "subject", "study_mode", "student_type", "postgraduate_type", "is_selected", 
                    "is_giveup", "is_alternate", "download_hx_file", "download_fq_file"]
    list_filter = ["subject"]
    search_fields = ["name"]
    actions = ['reset_password_to_exam_id']  # 添加自定义动作
    change_list_template = 'admin/student_change_list.html'

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "subject":
            # 使用自定义 ModelChoiceField 显示 subject_name (subject_type_display)
            kwargs["form_class"] = CustomModelChoiceField
            kwargs["queryset"] = Subject.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 添加自定义URL
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import-students/', self.admin_site.admin_view(self.import_students_view), name='import_students'),
            path('get-download-url/', self.admin_site.admin_view(self.get_download_url_view), name='get_download_url'),
        ]

        # 调试：打印所有 URL 模式
        # print("Custom URLs:", custom_urls)
        # print("All URLs:", urls)
        return custom_urls + urls

    # 处理CSV文件上传和学生创建的视图
    def import_students_view(self, request):
        if request.method == 'POST':
            form = ImportStudentForm(request.POST, request.FILES)
            if form.is_valid():
                csv_file = request.FILES['csv_file']
                try:
                    # 读取 CSV 文件
                    csv_file_wrapper = TextIOWrapper(csv_file, encoding='utf-8-sig')
                    reader = csv.DictReader(csv_file_wrapper)

                    
                    # 检查列名是否正确
                    required_columns = ["专业代码", "专业", "考生编号", "姓名", "初试成绩", "复试成绩", "综合成绩", "综合排名", "研究生类型", "学生类型", "手机号"]
                    if not all(column in reader.fieldnames for column in required_columns):
                        self.message_user(request, "CSV 文件列名不正确，请确保包含：准考证号、姓名、学生类型、研究生类型、学习方式", level='error')
                        return redirect('admin:Professor_Student_Manage_student_changelist')

                    # 创建学生账号
                    success_count = 0
                    for row in reader:
                        print(row)
                        subject_number = row["专业代码"]
                        subject_number = str(subject_number).zfill(6)
                        subject_name = row["专业"]

                        subject = Subject.objects.filter(subject_code=subject_number).first()
                        # print(subject)

                        candidate_number = str(row["考生编号"]).strip()
                        name = row["姓名"]
                        initial_exam_score = float(row["初试成绩"])
                        secondary_exam_score = float(row["复试成绩"])
                        # name = row["综合成绩"]
                        final_rank = row["综合排名"]

                        postgraduate_type = int(row["研究生类型"])  # 需转换为整数

                        student_type = int(row["学生类型"])  # 需转换为整数

                        phone_number = str(row["手机号"]).strip()
                        # study_mode  == "全日制"  # 转换为布尔值

                        try:
                            # 检查准考证号是否已存在
                            if Student.objects.filter(candidate_number=candidate_number).exists():
                                self.message_user(request, f"考生编号 {candidate_number} 已存在，跳过此记录", level='warning')
                                continue

                            # 创建关联的 User 对象
                            username = candidate_number  # 使用准考证号作为用户名
                            if User.objects.filter(username=username).exists():
                                self.message_user(request, f"用户名 {username} 已存在，跳过此记录", level='warning')
                                continue

                            user = User.objects.create_user(
                                username=username,
                                password=phone_number  # 初始密码设置为手机号
                            )
                            

                            # 创建 Student 对象
                            student = Student(
                                user_name=user,
                                name=name,
                                candidate_number=candidate_number,
                                subject = subject,
                                student_type=student_type,
                                postgraduate_type=postgraduate_type,
                                phone_number = phone_number,
                                initial_exam_score = initial_exam_score,
                                secondary_exam_score = secondary_exam_score,
                                final_rank = final_rank
                                # 其他字段使用默认值
                            )
                            student.save()
                            success_count += 1

                        except ValueError as e:
                            self.message_user(request, f"准考证号 {candidate_number} 的数据格式不正确: {str(e)}", level='warning')
                            continue
                        except Exception as e:
                            self.message_user(request, f"创建学生 {candidate_number} 时出错: {str(e)}", level='error')
                            continue
                        
                        # break

                    self.message_user(request, f"成功创建 {success_count} 个学生账号")
                    return redirect('admin:Professor_Student_Manage_student_changelist')

                except Exception as e:
                    self.message_user(request, f"解析 CSV 文件时出错: {str(e)}", level='error')
                    return redirect('admin:Professor_Student_Manage_student_changelist')
        else:
            form = ImportStudentForm()

        context = {
            'form': form,
            'opts': self.model._meta,
            'title': '一键导入学生账号',
        }
        return render(request, 'admin/import_students.html', context)
    

    def reset_password_to_exam_id(self, request, queryset):
        """
        将选中学生的密码重置为准考证号（exam_id）
        """
        for student in queryset:
            if student.user_name:  # 确保关联的 User 对象存在
                candidate_number = student.candidate_number
                student.user_name.set_password(candidate_number)  # 重置密码
                student.user_name.save()
                self.message_user(
                    request,
                    f"已重置学生 {student.name} 的密码为准考证号: {candidate_number}",
                    level='success'
                )

    reset_password_to_exam_id.short_description = "重置密码为准考证号"  # 动作显示名称

    # def download_fq_file(self, obj):
    #     """
    #     若学生已放弃拟录取并且 hx_file 有文件，则显示下载链接；否则显示 '-'
    #     """
    #     if obj.is_giveup == True:

    #         # 获取下载地址
    #         response_data_signature = self.get_fileid_download_url(obj.giveup_signature_table)
    #         if response_data_signature.get("errcode") == 0:
    #             signature_download_url = response_data_signature['file_list'][0]['download_url']
    #             print(f"放弃说明表下载地址: {signature_download_url}")
    #         else:
    #             return Response({'message': '获取放弃说明表下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #         return format_html(
    #             "<a href='{}' download>下载</a>", signature_download_url
    #         )
    #     return '未完成'

    # def download_hx_file(self, obj):
    #     """
    #     若学生已放弃拟录取并且 hx_file 有文件，则显示下载链接；否则显示 '-'
    #     """
    #     if obj.is_selected == True and obj.signature_table_review_status == 1:

    #         # 获取下载地址
    #         response_data_signature = self.get_fileid_download_url(obj.signature_table)
    #         if response_data_signature.get("errcode") == 0:
    #             signature_download_url = response_data_signature['file_list'][0]['download_url']
    #             print(f"签名图片下载地址: {signature_download_url}")
    #         else:
    #             return Response({'message': '获取签名图片下载地址失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    #         return format_html(
    #             "<a href='{}' download>下载</a>", signature_download_url
    #         )
    #     return '未完成'

    def get_download_url_view(self, request):
        """
        AJAX 视图，用于根据文件 ID 获取下载 URL
        """
        print("url访问成功")
        if request.method == 'POST':
            file_id = request.POST.get('file_id')
            if not file_id:
                return JsonResponse({'error': '未提供文件 ID'}, status=400)

            response_data = self.get_fileid_download_url(file_id)
            if response_data.get("errcode") == 0:
                download_url = response_data['file_list'][0]['download_url']
                return JsonResponse({'download_url': download_url})
            else:
                return JsonResponse({'error': '获取下载 URL 失败'}, status=500)

        return JsonResponse({'error': '无效的请求方法'}, status=405)

    def download_hx_file(self, obj):
        """
        如果满足条件，显示下载互选表的按钮
        """
        if obj.is_selected and obj.signature_table_review_status == 1 and obj.signature_table:
            return format_html(
                '<button class="download-btn" data-file-id="{}" data-type="hx">下载</button>',
                obj.signature_table
            )
        return '未完成'

    def download_fq_file(self, obj):
        """
        如果满足条件，显示下载弃选表的按钮
        """
        if obj.is_giveup and obj.giveup_signature_table:
            return format_html(
                '<button class="download-btn" data-file-id="{}" data-type="fq">下载</button>',
                obj.giveup_signature_table
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

    # change_list_template = 'admin/student_change_list.html'  # 自定义列表页面模板

    download_hx_file.short_description = "互选表下载"
    download_fq_file.short_description = "弃选表下载"


class WeChatAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "openid", "session_key"]


admin.site.register(Student, StudentAdmin)
admin.site.register(Professor, ProfessorAdmin)
admin.site.register(WeChatAccount, WeChatAccountAdmin)


