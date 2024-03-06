from django.contrib import admin
from django import forms

# Register your models here.
from .models import Student, Professor, WeChatAccount


class ProfessorAdmin(admin.ModelAdmin):
    fieldsets = [
        ("导师信息更改", {"fields": ["name", "teacher_identity_id", "email", "department", "enroll_subject",
                                     "academic_quota", "professional_quota", "professional_yt_quota", "doctor_quota", "proposed_quota_approved",
                                     "have_qualification", "remaining_quota", "personal_page", "research_areas",
                                     "avatar", "phone_number"]}),
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
                               "postgraduate_type", "study_mode", "resume", "avatar", "phone_number"]}),
    ]
    list_display = ["candidate_number", "name", "subject", "study_mode", "student_type", "postgraduate_type", "is_selected"]
    list_filter = ["subject"]
    search_fields = ["name"]


class WeChatAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "openid", "session_key"]


admin.site.register(Student, StudentAdmin)
admin.site.register(Professor, ProfessorAdmin)
admin.site.register(WeChatAccount, WeChatAccountAdmin)


