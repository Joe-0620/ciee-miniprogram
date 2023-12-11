from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils import timezone
from .views import approve_action
from .models import AdmissionQuotaApproval
from django.utils.html import format_html

class AdmissionQuotaApprovalAdmin(admin.ModelAdmin):
    # 列出需要设置为只读的字段
    readonly_fields = ["professor", "academic_quota", "professional_quota", "doctor_quota", "submit_date",
                       "reviewed_time"]
    list_display = ["professor", "academic_quota", "professional_quota", "doctor_quota",
                    "submit_date", "reviewed_by", "reviewed_time", "status", "action_button"]

    def action_button(self, obj):
        if obj.status == '0':
            approve_url = reverse('Professor_Quota_Review:approve_action', args=[obj.pk])
            reject_url = reverse('Professor_Quota_Review:reject_action', args=[obj.pk])
            buttons = [
                format_html('<a class="button" href="{}">通过</a>', approve_url),
                format_html('<a class="button" href="{}">拒绝</a>', reject_url)
            ]
            return format_html(' '.join(buttons))
        return ""

    action_button.short_description = '审核'
    actions = ["review_action"]

    def review_action(self, request, queryset):
        for approval in queryset:
            approval.status = '1'  # 设置为通过审核状态
            approval.reviewed_time = timezone.now()  # 更新审核时间
            approval.save()

            # 同步更新相关的 Professor 审核状态
            professor = approval.professor
            professor.proposed_quota_approved = True
            professor.save()

        self.message_user(request, f'{len(queryset)} 条记录已通过审核。')

    review_action.short_description = '批量通过审核'
    search_fields = ["professor__name_fk_search"]

admin.site.register(AdmissionQuotaApproval, AdmissionQuotaApprovalAdmin)