# Enrollment_Manage.models
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver

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

    total_admission_quota = models.PositiveIntegerField(default=0, verbose_name="总招生人数")

    subject_department = models.ManyToManyField(Department, related_name='subjects', verbose_name="可选该专业的方向")

    class Meta:
        verbose_name = "专业"  # 设置模型的显示名称
        verbose_name_plural = "专业"  # 设置模型的复数形式显示名称

    def __str__(self):
        return self.subject_name


@receiver(pre_save, sender=Subject)
def validate_and_sync_admission_quota(sender, instance, **kwargs):
    """
    当专业的总招生名额变更时：
    1. 验证减少名额时不能少于已分配的导师名额
    2. 自动同步候补学生状态
    """
    from Professor_Student_Manage.models import ProfessorMasterQuota, ProfessorDoctorQuota, Student
    from django.core.exceptions import ValidationError
    
    # 只处理已存在的专业（更新操作）
    if not instance.pk:
        return
    
    try:
        old_instance = Subject.objects.get(pk=instance.pk)
        old_quota = old_instance.total_admission_quota
        new_quota = instance.total_admission_quota
        
        # 如果名额没有变化，跳过
        if old_quota == new_quota:
            return
        
        # 计算该专业所有导师的名额总和（排除测试账号）
        if instance.subject_type in [0, 1]:  # 硕士专业
            total_assigned = ProfessorMasterQuota.objects.filter(
                subject=instance
            ).exclude(
                professor__teacher_identity_id__startswith='csds'
            ).aggregate(
                total=models.Sum(models.F('beijing_quota') + models.F('yantai_quota'))
            )['total'] or 0
        else:  # 博士专业
            total_assigned = ProfessorDoctorQuota.objects.filter(
                subject=instance
            ).exclude(
                professor__teacher_identity_id__startswith='csds'
            ).aggregate(total=models.Sum('total_quota'))['total'] or 0
        
        # 如果减少名额，验证不能少于已分配的导师名额
        if new_quota < old_quota and new_quota < total_assigned:
            raise ValidationError(
                f"专业 {instance.subject_name} 的总招生名额不能少于已分配的导师名额总和({total_assigned}人）。\n"
                f"当前设置: {new_quota}人，需要至少: {total_assigned}人。"
            )
        
    except Subject.DoesNotExist:
        pass


def sync_student_alternate_status(subject):
    """
    同步指定专业的学生候补状态
    根据专业总招生名额和学生排名自动调整候补状态
    """
    from Professor_Student_Manage.models import Student
    
    total_quota = subject.total_admission_quota or 0
    students = Student.objects.filter(subject=subject).order_by('final_rank')
    
    updated_count = 0
    for student in students:
        if student.final_rank and student.final_rank > 0:
            # 根据排名判断是否候补
            should_be_alternate = student.final_rank > total_quota
            new_alternate_rank = student.final_rank - total_quota if should_be_alternate else None
            
            # 只有状态变化时才更新
            if student.is_alternate != should_be_alternate or student.alternate_rank != new_alternate_rank:
                student.is_alternate = should_be_alternate
                student.alternate_rank = new_alternate_rank
                student.save(update_fields=['is_alternate', 'alternate_rank'])
                updated_count += 1
    
    return updated_count