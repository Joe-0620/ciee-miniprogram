from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Sum, Q
import json
from .models import Department, Subject
from Professor_Student_Manage.models import Professor, ProfessorMasterQuota, ProfessorDoctorQuota


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
    list_display = ["subject_name", "subject_code", "subject_type", "total_admission_quota_with_button", "allocated_quota_display"]
    
    class Media:
        css = {
            'all': ('admin/css/quota_modal.css',)
        }
        js = ('admin/js/quota_modal.js',)
    
    def total_admission_quota_with_button(self, obj):
        """
        显示总招生人数和调整按钮
        """
        quota = obj.total_admission_quota or 0
        return format_html(
            '<div style="display: flex; align-items: center; gap: 8px;">'
            '<span style="font-weight: 600; font-size: 15px; color: #333; min-width: 50px; text-align: right; display: inline-block;">{}</span>'
            '<a class="button" href="{}" style="padding: 5px 10px; background: #667eea; color: white; '
            'text-decoration: none; border-radius: 4px; font-size: 12px; white-space: nowrap;">📝 调整</a>'
            '</div>',
            quota,
            reverse('admin:adjust_subject_quota', args=[obj.pk])
        )
    
    total_admission_quota_with_button.short_description = "总招生人数"
    
    def allocated_quota_display(self, obj):
        """
        显示已分配给导师的名额，点击可查看详情
        """
        quota_data = {
            'subject_name': obj.subject_name,
            'subject_type': obj.subject_type,
            'quotas': []
        }
        
        if obj.subject_type == 2:  # 博士
            quotas = ProfessorDoctorQuota.objects.filter(subject=obj).exclude(
                professor__teacher_identity_id__startswith='csds'
            ).select_related('professor').order_by('professor__name')
            total_allocated = quotas.aggregate(total=Sum('total_quota'))['total'] or 0
            
            for quota in quotas:
                quota_data['quotas'].append({
                    'name': quota.professor.name,
                    'teacher_id': quota.professor.teacher_identity_id,
                    'total': quota.total_quota,
                    'used': quota.used_quota or 0,
                    'remaining': quota.remaining_quota or 0
                })
        else:  # 硕士（学硕或专硕）
            quotas = ProfessorMasterQuota.objects.filter(subject=obj).exclude(
                professor__teacher_identity_id__startswith='csds'
            ).select_related('professor').order_by('professor__name')
            total_bj = quotas.aggregate(total=Sum('beijing_quota'))['total'] or 0
            total_yt = quotas.aggregate(total=Sum('yantai_quota'))['total'] or 0
            total_allocated = total_bj + total_yt
            
            for quota in quotas:
                quota_data['quotas'].append({
                    'name': quota.professor.name,
                    'teacher_id': quota.professor.teacher_identity_id,
                    'bj_quota': quota.beijing_quota or 0,
                    'bj_remaining': quota.beijing_remaining_quota or 0,
                    'yt_quota': quota.yantai_quota or 0,
                    'yt_remaining': quota.yantai_remaining_quota or 0,
                    'total': (quota.beijing_quota or 0) + (quota.yantai_quota or 0)
                })
        
        # 生成详情字符串
        if total_allocated > 0:
            # 使用JSON序列化数据
            quota_json = json.dumps(quota_data, ensure_ascii=False)
            # HTML属性中只需要转义双引号和尖括号
            from html import escape
            quota_json_escaped = escape(quota_json, quote=True)
            
            return format_html(
                '<a href="#" class="quota-link" data-quota=\'{}\' '
                'style="color: #007bff; font-weight: bold; text-decoration: none; cursor: pointer;">'
                '📊 {} 人</a>',
                quota_json,  # 使用单引号包裹，内部的双引号不需要转义
                total_allocated
            )
        else:
            return format_html('<span style="color: #999;">0 人</span>')
    
    allocated_quota_display.short_description = "已分配名额"
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:subject_id>/adjust-quota/', self.admin_site.admin_view(self.adjust_quota_view), name='adjust_subject_quota'),
        ]
        return custom_urls + urls
    
    def adjust_quota_view(self, request, subject_id):
        """
        调整专业招生人数的视图
        """
        from django.shortcuts import render, redirect, get_object_or_404
        from django.contrib import messages
        from .models import sync_student_alternate_status
        from Professor_Student_Manage.models import Student
        
        subject = get_object_or_404(Subject, pk=subject_id)
        
        if request.method == 'POST':
            try:
                new_quota = int(request.POST.get('new_quota', 0))
                old_quota = subject.total_admission_quota or 0
                
                if new_quota < 0:
                    messages.error(request, "招生人数不能为负数")
                    return redirect('admin:Enrollment_Manage_subject_changelist')
                
                if new_quota == old_quota:
                    messages.info(request, "招生人数未发生变化")
                    return redirect('admin:Enrollment_Manage_subject_changelist')
                
                # 获取调整前的候补学生信息
                students_before = list(Student.objects.filter(
                    subject=subject, is_alternate=True
                ).values('id', 'name', 'final_rank', 'alternate_rank'))
                
                # 更新总招生名额
                subject.total_admission_quota = new_quota
                subject.save()
                
                # 同步候补状态
                updated_count = sync_student_alternate_status(subject)
                
                # 获取调整后的候补学生信息
                students_after_dict = {s.id: s for s in Student.objects.filter(subject=subject)}
                
                # 分析变化
                changes = []
                change_type = "增加" if new_quota > old_quota else "减少"
                quota_diff = abs(new_quota - old_quota)
                
                # 检查从候补转为正式的学生
                for student_info in students_before:
                    student_after = students_after_dict.get(student_info['id'])
                    if student_after and not student_after.is_alternate:
                        changes.append(f"✅ {student_info['name']} (排名{student_info['final_rank']}) 从候补{student_info['alternate_rank']}转为正式录取")
                
                # 检查从正式转为候补的学生
                for student in students_after_dict.values():
                    if student.is_alternate:
                        was_alternate = any(s['id'] == student.id for s in students_before)
                        if not was_alternate:
                            changes.append(f"⚠️ {student.name} (排名{student.final_rank}) 从正式录取转为候补{student.alternate_rank}")
                
                # 显示结果
                messages.success(request, f"专业 {subject.subject_name} 的总招生名额已从 {old_quota} {change_type}为 {new_quota} (变化{quota_diff}人)")
                if updated_count > 0:
                    messages.success(request, f"已自动调整 {updated_count} 名学生的候补状态")
                
                if changes:
                    for change in changes:
                        messages.info(request, change)
                else:
                    messages.info(request, "候补学生状态未发生变化")
                
                return redirect('admin:Enrollment_Manage_subject_changelist')
                
            except ValueError:
                messages.error(request, "请输入有效的数字")
                return redirect('admin:Enrollment_Manage_subject_changelist')
        
        # GET请求：显示调整页面
        context = {
            'subject': subject,
            'opts': self.model._meta,
            'title': f'调整 {subject.subject_name} 的招生人数',
        }
        return render(request, 'admin/adjust_subject_quota.html', context)
    
    def save_model(self, request, obj, form, change):
        """
        保存专业时，如果总招生名额发生变化，自动同步候补状态
        """
        from .models import sync_student_alternate_status
        from django.contrib import messages
        
        old_quota = None
        if change and obj.pk:
            try:
                old_instance = Subject.objects.get(pk=obj.pk)
                old_quota = old_instance.total_admission_quota
            except Subject.DoesNotExist:
                pass
        
        # 保存对象
        super().save_model(request, obj, form, change)
        
        # 如果名额发生变化，同步候补状态
        if old_quota is not None and old_quota != obj.total_admission_quota:
            updated_count = sync_student_alternate_status(obj)
            if updated_count > 0:
                messages.success(
                    request,
                    f"专业 {obj.subject_name} 的总招生名额已从 {old_quota} 更新为 {obj.total_admission_quota}，"
                    f"已自动调整 {updated_count} 名学生的候补状态。"
                )


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