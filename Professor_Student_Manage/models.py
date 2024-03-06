from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from Enrollment_Manage.models import Department, Subject


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
    personal_page = models.CharField(max_length=300, blank=True, verbose_name="个人介绍")
    avatar = models.CharField(max_length=500, null=True, blank=True, verbose_name="照片下载地址")

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
        self.remaining_quota = self.academic_quota + self.professional_quota + self.professional_yt_quota + self.doctor_quota
        super().save(*args, **kwargs)
        # print("触发super.save()")

    class Meta:
        verbose_name = "导师"  # 设置模型的显示名称
        verbose_name_plural = "导师"  # 设置模型的复数形式显示名称

    def __str__(self):
        return self.name


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
    resume = models.CharField(max_length=200, null=True, blank=True, verbose_name="简历")
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="手机号")
    # 初试成绩
    initial_exam_score = models.FloatField(null=True, blank=True)
    # 复试成绩
    secondary_exam_score = models.FloatField(null=True, blank=True)
    # 初试排名
    initial_rank = models.PositiveIntegerField(null=True, blank=True)
    # 复试排名
    secondary_rank = models.PositiveIntegerField(null=True, blank=True)
    # 总排名
    final_rank = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name = "学生"  # 设置模型的显示名称
        verbose_name_plural = "学生"  # 设置模型的复数形式显示名称

    def save(self, *args, **kwargs):
        self.name_fk_search = self.name
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name