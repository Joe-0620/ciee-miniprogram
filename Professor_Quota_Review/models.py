from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class AdmissionQuotaApproval(models.Model):
    # 外键指向导师（一个导师有一个审核）
    professor = models.ForeignKey('Professor_Student_Manage.Professor', on_delete=models.CASCADE,
                                  related_name='admission_quota_approvals', verbose_name="导师姓名")
    # 提议的指标
    academic_quota = models.IntegerField(default=0, verbose_name="学硕名额")
    professional_quota = models.IntegerField(default=0, verbose_name="专硕名额")
    doctor_quota = models.IntegerField(default=0, verbose_name="博士名额")
    # degree_doctor_quota = models.IntegerField(default=0)
    STATUS_CHOICES = [
        ('0', '等待审核'),
        ('1', '通过'),
        ('2', '拒绝'),
        ('3', '已取消')
    ]
    # 审核状态
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default='0', verbose_name="审核状态")
    # 审核人（待完善）
    reviewed_by = models.ForeignKey('Professor_Student_Manage.Professor', on_delete=models.CASCADE, null=True,
                                    blank=True, related_name='reviews_given', verbose_name="审核人")
    # 申请时间
    submit_date = models.DateTimeField(auto_now_add=True, verbose_name="提交时间")

    # 审核时间
    reviewed_time = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")


    class Meta:
        verbose_name = "导师指标审核"  # 设置模型的显示名称
        verbose_name_plural = "导师指标审核"  # 设置模型的复数形式显示名称

    def save(self, *args, **kwargs):
        # print("触发审核表save()")
        super().save(*args, **kwargs)
        # 获取关联的教授
        professor = self.professor
        # 检查关联的审核状态并更新教授的审核状态
        related_approvals = AdmissionQuotaApproval.objects.filter(professor=professor)
        has_approved_quota = any(approval.status == '1' for approval in related_approvals)
        professor.proposed_quota_approved = has_approved_quota
        professor.save()
        # print("审核表save()结束")


    def __str__(self):
        return f"{self.professor}"