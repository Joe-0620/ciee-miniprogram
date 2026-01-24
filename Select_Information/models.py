# Select_Information/models
from django.db import models
from Professor_Student_Manage.models import Student, Professor, ProfessorMasterQuota, ProfessorDoctorQuota
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from Enrollment_Manage.models import Department

class SelectionTime(models.Model):
    open_time = models.DateTimeField(verbose_name="开放时间")
    close_time = models.DateTimeField(verbose_name="关闭时间")

    def __str__(self):
        return f"开放时间：{self.open_time}, 关闭时间：{self.close_time}"
    
    class Meta:
        verbose_name = "学院师生互选时间设置"  # 设置模型的显示名称
        verbose_name_plural = "学院师生互选时间设置"  # 设置模型的复数形式显示名称

class StudentProfessorChoice(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="学生姓名")
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, verbose_name="导师姓名")

    STATUS_CHOICES = [
        [1, "已同意"],
        [2, "已拒绝"],
        [3, "请等待"],
        [4, "已取消"],
        [5, "已撤销"]
    ]
    status = models.IntegerField(default=3, choices=STATUS_CHOICES, verbose_name="状态")
    chosen_by_professor = models.BooleanField(default=False, verbose_name="是否选中")

    # 申请时间
    submit_date = models.DateTimeField(default=timezone.now, verbose_name="提交时间")

    # 审核时间
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")

    class Meta:
        verbose_name = "学院师生互选情况"  # 设置模型的显示名称
        verbose_name_plural = "学院师生互选情况"  # 设置模型的复数形式显示名称

    def __str__(self):
        return f"{self.student} - {self.professor}"

@receiver(post_save, sender=StudentProfessorChoice)
def update_used_quota(sender, instance, **kwargs):
    if instance.status != 1:  # 只有导师同意才更新
        return

    student = instance.student
    professor = instance.professor
    dept = professor.department

    if student.postgraduate_type == 2:  # 学硕
        quota = ProfessorMasterQuota.objects.filter(
            professor=professor, subject=student.subject
        ).first()
        if quota:
            # quota.beijing_remaining_quota -= 1  # 默认学硕算北京
            # quota.save()
            dept.used_academic_quota += 1

    elif student.postgraduate_type == 1:  # 北京专硕
        quota = ProfessorMasterQuota.objects.filter(
            professor=professor, subject=student.subject
        ).first()
        if quota and quota.beijing_remaining_quota > 0:
            # quota.beijing_remaining_quota -= 1
            # quota.save()
            dept.used_professional_quota += 1

    elif student.postgraduate_type == 4:  # 烟台专硕
        quota = ProfessorMasterQuota.objects.filter(
            professor=professor, subject=student.subject
        ).first()
        if quota and quota.yantai_remaining_quota > 0:
            # quota.yantai_remaining_quota -= 1
            # quota.save()
            dept.used_professional_yt_quota += 1

    elif student.postgraduate_type == 3:  # 博士
        quota = ProfessorDoctorQuota.objects.filter(
            professor=professor, subject=student.subject
        ).first()
        if quota and quota.remaining_quota > 0:
            # quota.used_quota += 1
            # quota.save()
            dept.used_doctor_quota += 1

    dept.save()

class ReviewRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="学生")
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, verbose_name="导师", related_name='review_records')
    file_id = models.CharField(max_length=500, verbose_name="文件ID")
    review_status = models.BooleanField(default=False, verbose_name="审核状态")
    submit_time = models.DateTimeField(default=timezone.now, verbose_name="提交时间")
    review_time = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    reviewer = models.ForeignKey(Professor, related_name='reviewer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="审核人")
    status = models.IntegerField(default=3, choices=[
        (1, "已通过"),
        (2, "已驳回"),
        (3, "待审核")
    ], verbose_name="状态")

    class Meta:
        verbose_name = "审核记录"
        verbose_name_plural = "审核记录"

    def __str__(self):
        return f"{self.student} - {self.professor} - {self.review_status}"

