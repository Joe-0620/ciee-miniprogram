# Professor_Student_Manage.models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from Enrollment_Manage.models import Department, Subject
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save
from django.dispatch import receiver

class WeChatAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    openid = models.CharField(max_length=255)
    session_key = models.CharField(max_length=255)

    class Meta:
        verbose_name = "微信账号绑定"  # 设置模型的显示名称
        verbose_name_plural = "微信账号绑定"  # 设置模型的复数形式显示名称


class Professor(models.Model):
    user_name = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="导师姓名")
    professor_title = models.CharField(max_length=10, default="副教授", null=False, verbose_name="导师职称")
    name_fk_search = models.CharField(max_length=100, verbose_name="导师(搜索专用)", null=True)
    teacher_identity_id = models.CharField(max_length=20, null=False, verbose_name="导师工号")
    email = models.EmailField(null=True, blank=True, verbose_name="导师邮箱")
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name="所属招生方向")
    enroll_subject = models.ManyToManyField(Subject, related_name='subjects', verbose_name="招生专业")
    research_areas = models.TextField(null=True, blank=True, verbose_name="研究方向")
    academic_quota = models.IntegerField(blank=True, default=0, verbose_name="学硕剩余名额")
    professional_quota = models.IntegerField(blank=True, default=0, verbose_name="专硕剩余名额")
    professional_yt_quota = models.IntegerField(blank=True, default=0, verbose_name="专硕(烟台)剩余名额")
    doctor_quota = models.IntegerField(blank=True, default=0, verbose_name="博士剩余名额")
    proposed_quota_approved = models.BooleanField(default=False, verbose_name="设置指标")
    have_qualification = models.BooleanField(default=True, verbose_name="招生资格")
    remaining_quota = models.IntegerField(default=0, verbose_name="总剩余名额")
    personal_page = models.CharField(max_length=500, blank=True, verbose_name="个人介绍")
    avatar = models.CharField(max_length=500, null=True, blank=True, verbose_name="照片下载地址")
    contact_details = models.CharField(max_length=100, null=True, blank=True, verbose_name="联系方式")
    signature_temp = models.CharField(max_length=500, null=True, blank=True, verbose_name="签名临时下载地址")
    website_order = models.IntegerField(default=0, verbose_name="官网排序号")

    Department_Position = [
        [0, "非审核人"],
        [1, "方向审核人(北京)"],
        [2, "方向审核人(烟台)"]
    ]

    department_position = models.IntegerField(choices=Department_Position, default=0, verbose_name="是否是审核人")
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="手机号码")


    def save(self, *args, **kwargs):
        # 获取之前的样例信息
        # original_instance = self.__class__.objects.get(pk=self.pk) if self.pk else None
        # print("获取之前的导师信息")
        original_instance = self.__class__.objects.filter(pk=self.pk).first()
        self.name_fk_search = self.name
        # 计算总剩余名额，包括博士专业名额
        doctor_quota_sum = sum(
            quota.remaining_quota for quota in self.doctor_quotas.filter(subject__subject_type=2)
        )
        self.doctor_quota = doctor_quota_sum
        self.remaining_quota = self.academic_quota + self.professional_quota + self.professional_yt_quota + self.doctor_quota
        super().save(*args, **kwargs)
        # print("触发super.save()")

    class Meta:
        verbose_name = "导师"  # 设置模型的显示名称
        verbose_name_plural = "导师"  # 设置模型的复数形式显示名称

    def __str__(self):
        return self.name

class ProfessorDoctorQuota(models.Model):
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, related_name='doctor_quotas', verbose_name="导师")
    subject = models.ForeignKey(
        Subject, 
        on_delete=models.CASCADE, 
        verbose_name="博士专业",
        limit_choices_to={'subject_type': 2}  # 限制为博士专业
    )
    total_quota = models.IntegerField(default=0, verbose_name="总招生名额")
    used_quota = models.IntegerField(default=0, verbose_name="已用名额")
    remaining_quota = models.IntegerField(default=0, verbose_name="剩余名额")

    def clean(self):
        # 确保已用名额不超过总名额
        if self.used_quota > self.total_quota:
            raise ValidationError("已用名额不能超过总名额")
        # 确保专业是博士类型
        if self.subject.subject_type != 2:
            raise ValidationError("只能选择博士专业")
        # 更新剩余名额
        self.remaining_quota = self.total_quota - self.used_quota

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        # 更新导师的 doctor_quota 和 remaining_quota
        self.professor.save()

    class Meta:
        verbose_name = "导师博士专业名额"
        verbose_name_plural = "导师博士专业名额"
        unique_together = [['professor', 'subject']]  # 确保每个导师在每个博士专业只有一个名额记录

    def __str__(self):
        return f"{self.professor.name} - {self.subject.subject_name} - 剩余: {self.remaining_quota}"

# 信号：当创建导师或博士专业时，初始化所有博士专业名额记录
@receiver(post_save, sender=Professor)
@receiver(post_save, sender=Subject)
def initialize_doctor_quotas(sender, instance, created, **kwargs):
    if sender == Professor and created:
        # 新建导师时，为所有博士专业创建名额记录
        doctor_subjects = Subject.objects.filter(subject_type=2)
        for subject in doctor_subjects:
            ProfessorDoctorQuota.objects.get_or_create(
                professor=instance,
                subject=subject,
                defaults={'total_quota': 0, 'used_quota': 0, 'remaining_quota': 0}
            )
    elif sender == Subject and created and instance.subject_type == 2:
        # 新建博士专业时，为所有导师创建名额记录
        professors = Professor.objects.all()
        for professor in professors:
            ProfessorDoctorQuota.objects.get_or_create(
                professor=professor,
                subject=instance,
                defaults={'total_quota': 0, 'used_quota': 0, 'remaining_quota': 0}
            )

class ProfessorMasterQuota(models.Model):
    """
    导师硕士专业名额（按地区拆分）
    """
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name='master_quotas',
        verbose_name="导师"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        limit_choices_to={'subject_type__in': [0, 1]},  # 限制为硕士专业
        verbose_name="硕士专业"
    )

    # 分配名额
    beijing_quota = models.IntegerField(default=0, verbose_name="北京可用名额")
    yantai_quota = models.IntegerField(default=0, verbose_name="烟台可用名额")

    # 剩余名额（只读，系统计算）
    beijing_remaining_quota = models.IntegerField(default=0, verbose_name="北京剩余名额")
    yantai_remaining_quota = models.IntegerField(default=0, verbose_name="烟台剩余名额")

    # 总招生名额（只读，系统计算）
    total_quota = models.IntegerField(default=0, verbose_name="硕士总招生名额")

    def save(self, *args, **kwargs):
        # 自动计算总数
        self.total_quota = self.beijing_quota + self.yantai_quota

        # 初始化时：剩余名额 = 可用名额
        if not self.pk:  # 新建对象
            self.beijing_remaining_quota = self.beijing_quota
            self.yantai_remaining_quota = self.yantai_quota
        else:
            # 如果剩余名额大于可用名额，自动修正
            if self.beijing_remaining_quota > self.beijing_quota:
                self.beijing_remaining_quota = self.beijing_quota
            if self.yantai_remaining_quota > self.yantai_quota:
                self.yantai_remaining_quota = self.yantai_quota

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "导师硕士专业名额"
        verbose_name_plural = "导师硕士专业名额"
        unique_together = [['professor', 'subject']]

    def __str__(self):
        return f"{self.professor.name} - {self.subject.subject_name} (总={self.total_quota}, 北京剩余={self.beijing_remaining_quota}, 烟台剩余={self.yantai_remaining_quota})"


# ========== 信号：新增导师或硕士专业时，自动初始化配额 ==========
@receiver(post_save, sender=Professor)
@receiver(post_save, sender=Subject)
def initialize_master_quotas(sender, instance, created, **kwargs):
    """
    当新增导师或硕士专业时，自动初始化对应的名额记录
    """
    if sender == Professor and created:
        # 新建导师时，为所有硕士专业创建配额记录
        master_subjects = Subject.objects.filter(subject_type__in=[0, 1])
        for subject in master_subjects:
            ProfessorMasterQuota.objects.get_or_create(
                professor=instance,
                subject=subject,
                defaults={'total_quota': 0}
            )

    elif sender == Subject and created and instance.subject_type in [0, 1]:
        # 新建硕士专业时，为所有导师创建配额记录
        professors = Professor.objects.all()
        for professor in professors:
            ProfessorMasterQuota.objects.get_or_create(
                professor=professor,
                subject=instance,
                defaults={'total_quota': 0}
            )


class Student(models.Model):
    # 用户名
    user_name = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="学生姓名")
    name_fk_search = models.CharField(max_length=100, verbose_name="学生(搜索专用)", null=True)
    candidate_number = models.CharField(max_length=20, unique=True, verbose_name="准考证号")
    subject = models.ForeignKey(Subject, null=True, on_delete=models.SET_NULL, verbose_name="报考专业")
    identify_number = models.CharField(max_length=20, unique=True, verbose_name="身份证号", null=True, blank=True)
    is_selected = models.BooleanField(default=False, verbose_name="是否选好导师")
    
    STUDENT_CHOICES = [
        [1, "硕士推免生"],
        [2, "硕士统考生"],
        [3, "博士统考生"],
    ]
    student_type = models.IntegerField(verbose_name="学生类型", choices=STUDENT_CHOICES)

    BACHELOR_TYPE = [
        [1, "专业型(北京)"],
        [2, "学术型"],
        [3, "博士"],
        [4, "专业型(烟台)"],
    ]
    postgraduate_type = models.IntegerField(verbose_name="研究生类型", choices=BACHELOR_TYPE)

    STUDY_MODE_CHOICES = [
        [True, "全日制"],
        [False, "非全日制"],
    ]
    study_mode = models.BooleanField(max_length=20, choices=STUDY_MODE_CHOICES, default=True, verbose_name="学习方式")
    avatar = models.CharField(max_length=200, null=True, blank=True, verbose_name="头像")
    signature_temp = models.CharField(max_length=500, null=True, blank=True, verbose_name="签名临时下载地址")
    signature_table = models.CharField(max_length=500, null=True, blank=True, verbose_name="导师意向表下载地址")
    giveup_signature_table = models.CharField(max_length=500, null=True, blank=True, verbose_name="放弃说明表下载地址")
    is_giveup = models.BooleanField(default=False, verbose_name="是否放弃拟录取")
    
    REVIEW_STATUS = [
        [1, "已同意"],
        [2, "已拒绝"],
        [3, "待审核"],
        [4, "未提交"]
    ]

    signature_table_student_signatured = models.BooleanField(default=False, verbose_name="学生签署导师意向表")
    signature_table_professor_signatured = models.BooleanField(default=False, verbose_name="导师签署导师意向表")
    signature_table_review_status = models.IntegerField(choices=REVIEW_STATUS, default=4, verbose_name="导师意向表审核状态")
    resume = models.CharField(max_length=200, null=True, blank=True, verbose_name="简历")
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="手机号")
    # 初试成绩
    initial_exam_score = models.FloatField(null=True, blank=True, verbose_name="初试成绩")
    # 复试成绩
    secondary_exam_score = models.FloatField(null=True, blank=True, verbose_name="复试成绩")
    # 初试排名
    initial_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="初试排名")
    # 复试排名
    secondary_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="复试排名")
    # 总排名
    final_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="总排名")
    # 新增：候补状态
    is_alternate = models.BooleanField(default=False, verbose_name="是否候补")

    class Meta:
        verbose_name = "学生"  # 设置模型的显示名称
        verbose_name_plural = "学生"  # 设置模型的复数形式显示名称

    def save(self, *args, **kwargs):
        self.name_fk_search = self.name
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name