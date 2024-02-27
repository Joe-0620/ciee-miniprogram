from django.contrib import admin

# Register your models here.
from .models import Student, Professor, Department


def check_department_head_or_deputy(modeladmin, request, queryset):
    # modeladmin: 这是一个 ModelAdmin 实例
    # request: 这是一个表示当前请求的对象
    # queryset: 这是一个 Django 查询集（QuerySet），包含了用户在管理界面中选择的所有对象。这是在执行操作时需要处理的对象集合。
    for department in queryset:
        has_department_head = Professor.objects.filter(department=department,
                                                       department_position__in=['1', '2']).exists()
        if has_department_head:
            message = f"{department.department_name} 有 方向负责人"
        else:
            message = f"{department.department_name} 没有 方向负责人"

        # message_user 用于向用户显示消息
        modeladmin.message_user(request, message)


check_department_head_or_deputy.short_description = "检查有没有方向负责人"


class ProfessorAdmin(admin.ModelAdmin):
    fieldsets = [
        ("导师信息更改", {"fields": ["name", "teacher_identity_id", "email", "department", "department_position",
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
        ("学生信息更改", {"fields": ["user_name", "name", "candidate_number", "student_type", "major", 
                               "major_direction", "specialty_code", "postgraduate_type", "study_mode", 
                               "resume", "avatar", "phone_number"]}),
    ]
    list_display = ["candidate_number", "name", "major", "major_direction", "study_mode", "student_type", "postgraduate_type", "is_selected"]
    list_filter = ["major"]
    search_fields = ["name"]


class DepartmentAdmin(admin.ModelAdmin):
    actions = [check_department_head_or_deputy]
    list_display = ["department_name", "total_academic_quota", "used_academic_quota", "total_professional_quota", 
                    "used_professional_quota", "total_doctor_quota", "used_doctor_quota", 
                    "has_department_head_or_deputy"]
    readonly_fields = ["used_academic_quota", "used_professional_quota", "used_doctor_quota"]

    # obj: 这是一个传入的参数，代表在管理页面中当前行对应的对象（即一个 Department 实例）。
    # 在每一行的单元格中，这个方法都会被调用，并且 obj 参数会传递当前行对应的 Department 实例。
    def has_department_head_or_deputy(self, department):
        department_head = Professor.objects.filter(department=department,
                                                   department_position__in=['1', '2'])
        return [professor for professor in department_head] if department_head else "无"

    has_department_head_or_deputy.short_description = "方向负责人"


# class AdmissionQuotaApprovalForm(forms.ModelForm):
#     class Meta:
#         model = AdmissionQuotaApproval
#         fields = '__all__'
#
#     def clean_academic_quota(self):
#         professional_quota = self.cleaned_data.get('professional_quota')
#         doctor_quota = self.cleaned_data.get('doctor_quota')
#         academic_quota = self.cleaned_data.get('academic_quota')
#
#         if academic_quota != professional_quota + doctor_quota:
#             raise forms.ValidationError("学硕名额必须等于专硕名额和博士名额之和。")
#
#         return academic_quota


admin.site.register(Student, StudentAdmin)
admin.site.register(Professor, ProfessorAdmin)
admin.site.register(Department, DepartmentAdmin)
