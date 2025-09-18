from django.contrib import admin
from .models import Department, Subject
from Professor_Student_Manage.models import Professor


# Register your models here.
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

class SubjectAdmin(admin.ModelAdmin):
    list_display = ["subject_name", "subject_code", "subject_type", "total_admission_quota"]


class DepartmentAdmin(admin.ModelAdmin):
    actions = [check_department_head_or_deputy]
    list_display = ["department_name", "total_academic_quota", "used_academic_quota", "total_professional_quota", 
                    "used_professional_quota", "total_professional_yt_quota", "used_professional_yt_quota", 
                    "has_department_head_or_deputy"]
    readonly_fields = ["used_academic_quota", "used_professional_quota", "used_doctor_quota"]

    # obj: 这是一个传入的参数，代表在管理页面中当前行对应的对象（即一个 Department 实例）。
    # 在每一行的单元格中，这个方法都会被调用，并且 obj 参数会传递当前行对应的 Department 实例。
    def has_department_head_or_deputy(self, department):
        department_head = Professor.objects.filter(department=department,
                                                   department_position__in=['1', '2'])
        return [professor for professor in department_head] if department_head else "无"

    has_department_head_or_deputy.short_description = "方向负责人"

admin.site.register(Department, DepartmentAdmin)
admin.site.register(Subject, SubjectAdmin)