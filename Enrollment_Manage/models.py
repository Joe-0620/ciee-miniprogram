# Enrollment_Manage.models
from django.db import models

# Create your models here.
class Department(models.Model):
    # 招生方向名称
    department_name = models.CharField(max_length=50, verbose_name="招生方向")

    # 方向学硕总招生指标
    total_academic_quota = models.IntegerField(null=False, default=0, verbose_name="学硕总指标")
    # 方向北京专硕总招生指标
    total_professional_quota = models.IntegerField(null=False, default=0, verbose_name="北京专硕总指标")
    # 方向烟台专硕总招生指标
    total_professional_yt_quota = models.IntegerField(null=False, default=0, verbose_name="烟台专硕总指标")
    # 方向学硕总招生指标
    total_doctor_quota = models.IntegerField(null=False, default=0, verbose_name="博士总指标")
    # 方向已用招生指标
    used_academic_quota = models.IntegerField(null=False, default=0, verbose_name="学硕已用指标")
    used_professional_quota = models.IntegerField(null=False, default=0, verbose_name="北京专硕已用指标")
    used_professional_yt_quota = models.IntegerField(null=False, default=0, verbose_name="烟台专硕已用指标")
    used_doctor_quota = models.IntegerField(null=False, default=0, verbose_name="博士已用指标")

    class Meta:
        verbose_name = "招生方向"  # 设置模型的显示名称
        verbose_name_plural = "招生方向"  # 设置模型的复数形式显示名称

    def __str__(self):
        return self.department_name
    

class Subject(models.Model):
    subject_name = models.CharField(max_length=50, verbose_name="专业名称")
    subject_code = models.CharField(max_length=10, verbose_name="专业代码")

    SubjectType = [
        [0, "专硕"],
        [1, "学硕"],
        [2, "博士"],
    ]
    subject_type = models.IntegerField(choices=SubjectType, verbose_name="专业所属类别")
    subject_department = models.ManyToManyField(Department, related_name='subjects', verbose_name="可选该专业的方向")

    class Meta:
        verbose_name = "专业"  # 设置模型的显示名称
        verbose_name_plural = "专业"  # 设置模型的复数形式显示名称

    def __str__(self):
        return self.subject_name