from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from Professor_Student_Manage.models import (
    Professor,
    ProfessorDoctorQuota,
    ProfessorMasterQuota,
    ProfessorSharedQuotaPool,
    Student,
)


class SelectionTime(models.Model):
    TARGET_STUDENT = 'student'
    TARGET_PROFESSOR = 'professor'
    TARGET_CHOICES = [
        (TARGET_STUDENT, '学生'),
        (TARGET_PROFESSOR, '导师'),
    ]

    target = models.CharField(max_length=20, choices=TARGET_CHOICES, unique=True, default=TARGET_STUDENT)
    open_time = models.DateTimeField(verbose_name="开放时间")
    close_time = models.DateTimeField(verbose_name="关闭时间")

    class Meta:
        verbose_name = "学院师生互选时间设置"
        verbose_name_plural = "学院师生互选时间设置"

    def __str__(self):
        return f"{self.get_target_display()}：{self.open_time} - {self.close_time}"


class StudentProfessorChoice(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="学生姓名")
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, verbose_name="导师姓名")
    shared_quota_pool = models.ForeignKey(
        ProfessorSharedQuotaPool,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='choices',
        verbose_name="消耗的共享名额池",
    )

    STATUS_CHOICES = [
        (1, "已同意"),
        (2, "已拒绝"),
        (3, "请等待"),
        (4, "已取消"),
        (5, "已撤销"),
    ]
    status = models.IntegerField(default=3, choices=STATUS_CHOICES, verbose_name="状态")
    chosen_by_professor = models.BooleanField(default=False, verbose_name="是否选中")
    submit_date = models.DateTimeField(default=timezone.now, verbose_name="提交时间")
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")

    class Meta:
        verbose_name = "学院师生互选情况"
        verbose_name_plural = "学院师生互选情况"

    def __str__(self):
        return f"{self.student} - {self.professor}"


@receiver(post_save, sender=StudentProfessorChoice)
def update_used_quota(sender, instance, **kwargs):
    if instance.status != 1:
        return

    student = instance.student
    professor = instance.professor
    dept = professor.department

    if instance.shared_quota_pool_id:
        if student.postgraduate_type == 2:
            dept.used_academic_quota += 1
        elif student.postgraduate_type == 1:
            dept.used_professional_quota += 1
        elif student.postgraduate_type == 4:
            dept.used_professional_yt_quota += 1
        elif student.postgraduate_type == 3:
            dept.used_doctor_quota += 1
        dept.save()
        return

    if student.postgraduate_type == 2:
        quota = ProfessorMasterQuota.objects.filter(professor=professor, subject=student.subject).first()
        if quota:
            dept.used_academic_quota += 1
    elif student.postgraduate_type == 1:
        quota = ProfessorMasterQuota.objects.filter(professor=professor, subject=student.subject).first()
        if quota and quota.beijing_remaining_quota > 0:
            dept.used_professional_quota += 1
    elif student.postgraduate_type == 4:
        quota = ProfessorMasterQuota.objects.filter(professor=professor, subject=student.subject).first()
        if quota and quota.yantai_remaining_quota > 0:
            dept.used_professional_yt_quota += 1
    elif student.postgraduate_type == 3:
        quota = ProfessorDoctorQuota.objects.filter(professor=professor, subject=student.subject).first()
        if quota and quota.remaining_quota > 0:
            dept.used_doctor_quota += 1

    dept.save()


class ReviewRecord(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="学生")
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, verbose_name="导师", related_name='review_records')
    file_id = models.CharField(max_length=500, verbose_name="文件 ID")
    review_status = models.BooleanField(default=False, verbose_name="审核状态")
    submit_time = models.DateTimeField(default=timezone.now, verbose_name="提交时间")
    review_time = models.DateTimeField(null=True, blank=True, verbose_name="审核时间")
    reviewer = models.ForeignKey(Professor, related_name='reviewer', on_delete=models.SET_NULL, null=True, blank=True, verbose_name="审核人")
    status = models.IntegerField(
        default=3,
        choices=[
            (1, "已通过"),
            (2, "已驳回"),
            (3, "待审核"),
        ],
        verbose_name="状态",
    )

    class Meta:
        verbose_name = "审核记录"
        verbose_name_plural = "审核记录"

    def __str__(self):
        return f"{self.student} - {self.professor} - {self.review_status}"
