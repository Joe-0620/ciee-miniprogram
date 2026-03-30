# Professor_Student_Manage.models
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from Enrollment_Manage.models import Department, Subject
from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.db.models import Sum, Q, F, Count
from django.db.models.functions import Coalesce
from django.db import transaction
from django.core.cache import cache
from rest_framework.authtoken.models import Token


class WeChatAccount(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    openid = models.CharField(max_length=255)
    session_key = models.CharField(max_length=255)

    class Meta:
        verbose_name = "微信账号绑定"  # 设置模型的显示名称
        verbose_name_plural = "微信账号绑定"  # 设置模型的复数显示名称


class Professor(models.Model):
    HEAT_LEVEL_LOW = '低'
    HEAT_LEVEL_MEDIUM = '中'
    HEAT_LEVEL_HIGH = '高'
    HEAT_LEVEL_VERY_HIGH = '很高'
    HEAT_LEVEL_CHOICES = [
        (HEAT_LEVEL_LOW, '低'),
        (HEAT_LEVEL_MEDIUM, '中'),
        (HEAT_LEVEL_HIGH, '高'),
        (HEAT_LEVEL_VERY_HIGH, '很高'),
    ]

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
    proposed_quota_approved = models.BooleanField(default=False, verbose_name="开放被选择资格")
    have_qualification = models.BooleanField(default=True, verbose_name="招生资格")
    remaining_quota = models.IntegerField(default=0, verbose_name="总剩余名额")
    personal_page = models.CharField(max_length=500, blank=True, verbose_name="个人介绍")
    avatar = models.CharField(max_length=500, null=True, blank=True, verbose_name="照片下载地址")
    contact_details = models.CharField(max_length=100, null=True, blank=True, verbose_name="联系方式")
    signature_temp = models.CharField(max_length=500, null=True, blank=True, verbose_name="签名临时下载地址")
    website_order = models.IntegerField(default=0, verbose_name="官网排序号")
    heat_display_enabled = models.BooleanField(default=True, verbose_name="前端是否显示热度")
    manual_heat_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="手动热度指数")
    manual_heat_level = models.CharField(
        max_length=10,
        choices=HEAT_LEVEL_CHOICES,
        null=True,
        blank=True,
        verbose_name="手动热度等级",
    )

    Department_Position = [
        [0, "非审核人"],
        [1, "方向审核人(北京)"],
        [2, "方向审核人(烟台)"]
    ]

    department_position = models.IntegerField(choices=Department_Position, default=0, verbose_name="是否为审核人")
    phone_number = models.CharField(max_length=20, null=True, blank=True, verbose_name="手机号码")


    def save(self, *args, **kwargs):
        # 获取保存前的导师信息
        # original_instance = self.__class__.objects.get(pk=self.pk) if self.pk else None
        # print("获取之前的导师信息")
        original_instance = self.__class__.objects.filter(pk=self.pk).first()
        self.name_fk_search = self.name
        # 计算总剩余名额，包括博士专业名额和共享池名额
        doctor_quota_sum = sum(
            quota.remaining_quota for quota in self.doctor_quotas.filter(subject__subject_type=2)
        )
        self.doctor_quota = doctor_quota_sum
        shared_pool_quota_sum = sum(
            pool.remaining_quota for pool in self.shared_quota_pools.filter(is_active=True)
        ) if self.pk else 0
        self.remaining_quota = (
            self.academic_quota
            + self.professional_quota
            + self.professional_yt_quota
            + self.doctor_quota
            + shared_pool_quota_sum
        )
        super().save(*args, **kwargs)
        # print("触发 super.save()")

    class Meta:
        verbose_name = "导师"  # 设置模型的显示名称
        verbose_name_plural = "导师"  # 设置模型的复数显示名称

    def __str__(self):
        return self.name


class ProfessorSharedQuotaPool(models.Model):
    SCOPE_MASTER = 'master'
    SCOPE_DOCTOR = 'doctor'
    SCOPE_CHOICES = [
        (SCOPE_MASTER, '硕士共享池'),
        (SCOPE_DOCTOR, '博士共享池'),
    ]

    CAMPUS_GENERAL = 'general'
    CAMPUS_BEIJING = 'beijing'
    CAMPUS_YANTAI = 'yantai'
    CAMPUS_CHOICES = [
        (CAMPUS_GENERAL, '不区分校区'),
        (CAMPUS_BEIJING, '北京'),
        (CAMPUS_YANTAI, '烟台'),
    ]

    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name='shared_quota_pools',
        verbose_name="导师",
    )
    pool_name = models.CharField(max_length=100, verbose_name="共享名额池名称")
    quota_scope = models.CharField(max_length=20, choices=SCOPE_CHOICES, verbose_name="名额类型")
    campus = models.CharField(max_length=20, choices=CAMPUS_CHOICES, default=CAMPUS_GENERAL, verbose_name="适用校区")
    subjects = models.ManyToManyField(Subject, related_name='shared_quota_pools', verbose_name="可使用专业")
    total_quota = models.IntegerField(default=0, verbose_name="总名额")
    used_quota = models.IntegerField(default=0, verbose_name="已用名额")
    remaining_quota = models.IntegerField(default=0, verbose_name="剩余名额")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    notes = models.TextField(blank=True, default="", verbose_name="备注")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def clean(self):
        if self.total_quota < 0 or self.used_quota < 0 or self.remaining_quota < 0:
            raise ValidationError("名额字段必须是非负整数")
        if self.used_quota > self.total_quota:
            raise ValidationError("已用名额不能大于总名额")
        if self.quota_scope == self.SCOPE_DOCTOR and self.campus != self.CAMPUS_GENERAL:
            raise ValidationError("博士共享池不能设置北京或烟台校区")

    def save(self, *args, **kwargs):
        self.clean()
        if self.remaining_quota > self.total_quota:
            self.remaining_quota = self.total_quota
        super().save(*args, **kwargs)
        recalculate_professor_quota_summary(self.professor)


    class Meta:
        verbose_name = "导师共享名额池"
        verbose_name_plural = "导师共享名额池"

    def __str__(self):
        return f"{self.professor.name} - {self.pool_name}"


class ProfessorProfileSection(models.Model):
    professor = models.ForeignKey(
        Professor,
        on_delete=models.CASCADE,
        related_name='profile_sections',
        verbose_name="导师",
    )
    title = models.CharField(max_length=50, verbose_name="模块标题")
    content = models.TextField(verbose_name="模块内容")
    sort_order = models.IntegerField(default=0, verbose_name="排序值")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "导师主页自定义模块"
        verbose_name_plural = "导师主页自定义模块"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.professor.name} - {self.title}"


class ProfessorHeatDisplaySetting(models.Model):
    CALCULATION_SCOPE_OVERALL = 'overall'
    CALCULATION_SCOPE_SUBJECT = 'subject'
    CALCULATION_SCOPE_CHOICES = [
        (CALCULATION_SCOPE_OVERALL, '按导师总量计算'),
        (CALCULATION_SCOPE_SUBJECT, '按当前学生专业计算'),
    ]

    show_professor_heat = models.BooleanField(default=True, verbose_name="前端是否显示导师热度")
    calculation_scope = models.CharField(
        max_length=20,
        choices=CALCULATION_SCOPE_CHOICES,
        default=CALCULATION_SCOPE_SUBJECT,
        verbose_name="热度计算维度",
    )
    target_admission_year = models.PositiveIntegerField(default=2026, verbose_name="统计届别")
    pending_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.00, verbose_name="待处理人数权重")
    accepted_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="已同意人数权重")
    rejected_weight = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, verbose_name="已拒绝人数权重")
    medium_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=2.00, verbose_name="二级热度超出阈值")
    high_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=4.00, verbose_name="三级热度超出阈值")
    very_high_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=6.00, verbose_name="四级热度超出阈值")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "导师热度显示配置"
        verbose_name_plural = "导师热度显示配置"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('professor_heat_display_setting')

    def delete(self, *args, **kwargs):
        return

    def __str__(self):
        return '导师热度显示配置'


def get_professor_heat_display_setting():
    cache_key = 'professor_heat_display_setting'
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    setting, _ = ProfessorHeatDisplaySetting.objects.get_or_create(pk=1)
    cache.set(cache_key, setting, timeout=300)
    return setting


def _get_prefetched_related_list(instance, relation_name):
    cache = getattr(instance, '_prefetched_objects_cache', {})
    if relation_name in cache:
        return list(cache[relation_name])
    return list(getattr(instance, relation_name).all())


def _get_pool_subjects(pool):
    cache = getattr(pool, '_prefetched_objects_cache', {})
    if 'subjects' in cache:
        return list(cache['subjects'])
    return list(pool.subjects.all())


def resolve_heat_level_by_setting(heat_score, setting=None):
    if setting is None:
        setting = get_professor_heat_display_setting()
    medium_threshold = float(getattr(setting, 'medium_threshold', 2) or 2)
    high_threshold = float(getattr(setting, 'high_threshold', 4) or 4)
    very_high_threshold = float(getattr(setting, 'very_high_threshold', 6) or 6)

    if heat_score >= very_high_threshold:
        return Professor.HEAT_LEVEL_VERY_HIGH
    if heat_score >= high_threshold:
        return Professor.HEAT_LEVEL_HIGH
    if heat_score >= medium_threshold:
        return Professor.HEAT_LEVEL_MEDIUM
    return Professor.HEAT_LEVEL_LOW


def calculate_professor_subject_available_quota(professor, subject=None, postgraduate_type=None):
    if subject is None:
        return 0

    available_quota_total = 0
    master_quotas = _get_prefetched_related_list(professor, 'master_quotas')
    doctor_quotas = _get_prefetched_related_list(professor, 'doctor_quotas')
    shared_pools = [
        pool for pool in _get_prefetched_related_list(professor, 'shared_quota_pools')
        if getattr(pool, 'is_active', False)
    ]

    if postgraduate_type == 3:
        quota = next((item for item in doctor_quotas if item.subject_id == subject.id), None)
        available_quota_total += (quota.remaining_quota or 0) if quota else 0
        shared_total = sum(
            pool.remaining_quota or 0
            for pool in shared_pools
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_DOCTOR
            and any(item.id == subject.id for item in _get_pool_subjects(pool))
        )
        available_quota_total += shared_total
        return max(int(available_quota_total or 0), 0)

    if postgraduate_type in [1, 2, 4]:
        quota = next((item for item in master_quotas if item.subject_id == subject.id), None)
        if quota:
            if postgraduate_type == 4:
                available_quota_total += quota.yantai_remaining_quota or 0
            else:
                available_quota_total += quota.beijing_remaining_quota or 0

        target_campus = (
            ProfessorSharedQuotaPool.CAMPUS_YANTAI
            if postgraduate_type == 4 else ProfessorSharedQuotaPool.CAMPUS_BEIJING
        )
        shared_total = sum(
            pool.remaining_quota or 0
            for pool in shared_pools
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER
            and pool.campus == target_campus
            and any(item.id == subject.id for item in _get_pool_subjects(pool))
        )
        available_quota_total += shared_total
        return max(int(available_quota_total or 0), 0)

    if subject.subject_type == 2:
        quota = next((item for item in doctor_quotas if item.subject_id == subject.id), None)
        available_quota_total += (quota.remaining_quota or 0) if quota else 0
        shared_total = sum(
            pool.remaining_quota or 0
            for pool in shared_pools
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_DOCTOR
            and any(item.id == subject.id for item in _get_pool_subjects(pool))
        )
        available_quota_total += shared_total
    elif subject.subject_type == 1:
        quota = next((item for item in master_quotas if item.subject_id == subject.id), None)
        available_quota_total += (quota.beijing_remaining_quota or 0) if quota else 0
        shared_total = sum(
            pool.remaining_quota or 0
            for pool in shared_pools
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER
            and pool.campus == ProfessorSharedQuotaPool.CAMPUS_BEIJING
            and any(item.id == subject.id for item in _get_pool_subjects(pool))
        )
        available_quota_total += shared_total
    else:
        quota = next((item for item in master_quotas if item.subject_id == subject.id), None)
        if quota:
            available_quota_total += (quota.beijing_remaining_quota or 0) + (quota.yantai_remaining_quota or 0)
        shared_total = sum(
            pool.remaining_quota or 0
            for pool in shared_pools
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER
            and pool.campus in [ProfessorSharedQuotaPool.CAMPUS_BEIJING, ProfessorSharedQuotaPool.CAMPUS_YANTAI]
            and any(item.id == subject.id for item in _get_pool_subjects(pool))
        )
        available_quota_total += shared_total

    return max(int(available_quota_total or 0), 0)


class AvailableStudentDisplaySetting(models.Model):
    enabled = models.BooleanField(default=True, verbose_name="是否开放可选学生展示")
    require_resume = models.BooleanField(default=False, verbose_name="仅展示已上传简历学生")
    allowed_admission_years = models.JSONField(default=list, blank=True, verbose_name="允许展示届别")
    allowed_batch_ids = models.JSONField(default=list, blank=True, verbose_name="允许展示批次")
    allowed_postgraduate_types = models.JSONField(default=list, blank=True, verbose_name="允许展示培养类型")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "可选学生展示配置"
        verbose_name_plural = "可选学生展示配置"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
        cache.delete('available_student_display_setting')

    def delete(self, *args, **kwargs):
        return

    def __str__(self):
        return '可选学生展示配置'


def get_available_student_display_setting():
    cache_key = 'available_student_display_setting'
    cached_value = cache.get(cache_key)
    if cached_value is not None:
        return cached_value
    setting, _ = AvailableStudentDisplaySetting.objects.get_or_create(pk=1)
    cache.set(cache_key, setting, timeout=300)
    return setting


def normalize_available_student_display_values(values):
    normalized_values = []
    for value in values or []:
        try:
            normalized_value = int(value)
        except (TypeError, ValueError):
            continue
        if normalized_value not in normalized_values:
            normalized_values.append(normalized_value)
    return normalized_values


def get_student_quota_scope(student):
    return ProfessorSharedQuotaPool.SCOPE_DOCTOR if student.postgraduate_type == 3 else ProfessorSharedQuotaPool.SCOPE_MASTER


def get_student_campus(student):
    if student.postgraduate_type == 4:
        return ProfessorSharedQuotaPool.CAMPUS_YANTAI
    if student.postgraduate_type in [1, 2]:
        return ProfessorSharedQuotaPool.CAMPUS_BEIJING
    return ProfessorSharedQuotaPool.CAMPUS_GENERAL


def get_matching_shared_quota_pool(professor, student, remaining_only=False):
    queryset = ProfessorSharedQuotaPool.objects.filter(
        professor=professor,
        quota_scope=get_student_quota_scope(student),
        is_active=True,
        subjects=student.subject,
    )
    if student.postgraduate_type != 3:
        queryset = queryset.filter(campus=get_student_campus(student))
    if remaining_only:
        queryset = queryset.filter(remaining_quota__gt=0)
    return queryset.order_by('id').first()


def get_quota_source_for_student(professor, student, remaining_only=False):
    shared_pool = get_matching_shared_quota_pool(professor, student, remaining_only=remaining_only)
    if shared_pool:
        return 'shared', shared_pool

    if student.postgraduate_type == 3:
        quota = ProfessorDoctorQuota.objects.filter(professor=professor, subject=student.subject).first()
        if quota and (not remaining_only or (quota.remaining_quota or 0) > 0):
            return 'doctor', quota
        return None, None

    quota = ProfessorMasterQuota.objects.filter(professor=professor, subject=student.subject).first()
    if not quota:
        return None, None
    if not remaining_only:
        return 'master', quota
    if student.postgraduate_type in [1, 2] and (quota.beijing_remaining_quota or 0) > 0:
        return 'master', quota
    if student.postgraduate_type == 4 and (quota.yantai_remaining_quota or 0) > 0:
        return 'master', quota
    return None, None


def recalculate_professor_quota_summary(professor):
    academic_quota = (
        professor.master_quotas.filter(subject__subject_type=1).aggregate(total=Coalesce(Sum('beijing_remaining_quota'), 0))['total']
        or 0
    )
    professional_quota = (
        professor.master_quotas.filter(subject__subject_type=0).aggregate(total=Coalesce(Sum('beijing_remaining_quota'), 0))['total']
        or 0
    )
    professional_yt_quota = (
        professor.master_quotas.filter(subject__subject_type=0).aggregate(total=Coalesce(Sum('yantai_remaining_quota'), 0))['total']
        or 0
    )
    doctor_quota = (
        professor.doctor_quotas.aggregate(total=Coalesce(Sum('remaining_quota'), 0))['total']
        or 0
    )
    shared_pool_quota = (
        professor.shared_quota_pools.filter(is_active=True).aggregate(total=Coalesce(Sum('remaining_quota'), 0))['total']
        or 0
    )
    Professor.objects.filter(pk=professor.pk).update(
        academic_quota=academic_quota,
        professional_quota=professional_quota,
        professional_yt_quota=professional_yt_quota,
        doctor_quota=doctor_quota,
        remaining_quota=academic_quota + professional_quota + professional_yt_quota + doctor_quota + shared_pool_quota,
    )


def calculate_professor_heat_metrics(professor, setting=None):
    if setting is None:
        setting = get_professor_heat_display_setting()

    pending_count = 0
    accepted_count = 0
    rejected_count = 0

    if hasattr(professor, 'pending_choice_count') and professor.pending_choice_count is not None:
        pending_count = professor.pending_choice_count
    if hasattr(professor, 'accepted_choice_count') and professor.accepted_choice_count is not None:
        accepted_count = professor.accepted_choice_count
    if hasattr(professor, 'rejected_choice_count') and professor.rejected_choice_count is not None:
        rejected_count = professor.rejected_choice_count

    if pending_count == 0 and accepted_count == 0 and rejected_count == 0:
        choice_queryset = getattr(professor, 'studentprofessorchoice_set', None)
        if choice_queryset is None:
            return {
                'pending_count': pending_count,
                'accepted_count': accepted_count,
                'rejected_count': rejected_count,
                'available_quota_total': max(int(getattr(professor, 'remaining_quota', 0) or 0), 0),
                'heat_score': 0,
                'heat_level': Professor.HEAT_LEVEL_LOW,
            }
        choice_stats = choice_queryset.aggregate(
            pending_count=Count('id', filter=Q(status=3)),
            accepted_count=Count('id', filter=Q(status=1)),
            rejected_count=Count('id', filter=Q(status=2)),
        )
        pending_count = choice_stats.get('pending_count') or 0
        accepted_count = choice_stats.get('accepted_count') or 0
        rejected_count = choice_stats.get('rejected_count') or 0

    available_quota_total = max(int(getattr(professor, 'remaining_quota', 0) or 0), 0)
    pending_weight = float(getattr(setting, 'pending_weight', 1) or 1)
    accepted_weight = float(getattr(setting, 'accepted_weight', 0.6) or 0)
    rejected_weight = float(getattr(setting, 'rejected_weight', 0.2) or 0)
    weighted_demand = (
        pending_count * pending_weight
        + accepted_count * accepted_weight
        + rejected_count * rejected_weight
    )
    heat_score = round(weighted_demand / max(available_quota_total, 1), 2)
    heat_level = resolve_heat_level_by_setting(heat_score, setting=setting)

    return {
        'pending_count': pending_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'available_quota_total': available_quota_total,
        'weighted_demand': round(weighted_demand, 2),
        'heat_score': heat_score,
        'heat_level': heat_level,
    }


def calculate_professor_subject_heat_metrics(professor, subject=None, postgraduate_type=None, setting=None, student_type=None):
    if setting is None:
        setting = get_professor_heat_display_setting()

    if subject is None:
        return {
            'pending_count': 0,
            'accepted_count': 0,
            'rejected_count': 0,
            'available_quota_total': 0,
            'heat_score': 0,
            'heat_level': resolve_heat_level_by_setting(0, setting=setting),
        }

    choice_queryset = professor.studentprofessorchoice_set.filter(student__subject=subject)
    if postgraduate_type:
        choice_queryset = choice_queryset.filter(student__postgraduate_type=postgraduate_type)
    if student_type:
        choice_queryset = choice_queryset.filter(student__student_type=student_type)
    target_admission_year = getattr(setting, 'target_admission_year', None)
    if target_admission_year not in (None, ''):
        choice_queryset = choice_queryset.filter(student__admission_year=target_admission_year)

    choice_stats = choice_queryset.aggregate(
        pending_count=Count('id', filter=Q(status=3)),
    )
    pending_count = choice_stats.get('pending_count') or 0
    accepted_count = 0
    rejected_count = 0

    available_quota_total = calculate_professor_subject_available_quota(
        professor,
        subject=subject,
        postgraduate_type=postgraduate_type,
    )
    overflow_count = max(pending_count - available_quota_total, 0)
    heat_score = round(float(overflow_count), 2)
    heat_level = resolve_heat_level_by_setting(heat_score, setting=setting)

    return {
        'pending_count': pending_count,
        'accepted_count': accepted_count,
        'rejected_count': rejected_count,
        'available_quota_total': max(int(available_quota_total or 0), 0),
        'overflow_count': overflow_count,
        'heat_score': heat_score,
        'heat_level': heat_level,
    }


def get_professor_heat_display_metrics(professor, global_setting=None, subject=None, postgraduate_type=None, student_type=None):
    if global_setting is None:
        global_setting = get_professor_heat_display_setting()
    metrics = calculate_professor_subject_heat_metrics(
        professor,
        subject=subject,
        postgraduate_type=postgraduate_type,
        setting=global_setting,
        student_type=student_type,
    )
    manual_heat_score = getattr(professor, 'manual_heat_score', None)
    manual_heat_level = getattr(professor, 'manual_heat_level', None)

    if manual_heat_score is not None:
        heat_score = round(float(manual_heat_score), 2)
    else:
        heat_score = metrics['heat_score']

    if manual_heat_level:
        heat_level = manual_heat_level
    else:
        heat_level = resolve_heat_level_by_setting(heat_score, setting=global_setting)

    heat_visible = bool(getattr(global_setting, 'show_professor_heat', True)) and bool(
        getattr(professor, 'heat_display_enabled', True)
    )
    if subject is not None and (metrics.get('available_quota_total') or 0) <= 0:
        heat_visible = False

    return {
        **metrics,
        'calculation_scope': ProfessorHeatDisplaySetting.CALCULATION_SCOPE_SUBJECT,
        'subject_heat': True,
        'target_admission_year': getattr(global_setting, 'target_admission_year', 2026),
        'heat_score': heat_score,
        'heat_level': heat_level,
        'heat_visible': heat_visible,
        'heat_display_enabled': getattr(professor, 'heat_display_enabled', True),
        'manual_heat_score': manual_heat_score,
        'manual_heat_level': manual_heat_level or '',
    }

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
        unique_together = [['professor', 'subject']]  # 确保每个导师在每个博士专业下只有一条名额记录

    def __str__(self):
        return f"{self.professor.name} - {self.subject.subject_name} - 剩余: {self.remaining_quota}"

# 信号：当创建博士专业时，初始化所有导师对应的博士名额记录
# @receiver(post_save, sender=Professor)
@receiver(post_save, sender=Subject)
def initialize_doctor_quotas(sender, instance, created, **kwargs):
    """当新增博士专业时，自动为所有导师创建对应的博士配额记录。"""
    if created and instance.subject_type == 2:  # 限制为博士专业
        professors = Professor.objects.all()
        for professor in professors:
            ProfessorDoctorQuota.objects.get_or_create(
                professor=professor,
                subject=instance,
                defaults={
                    'total_quota': 0,
                    'used_quota': 0,
                    'remaining_quota': 0
                }
            )

class ProfessorMasterQuota(models.Model):
    """导师硕士专业名额，按校区拆分。"""
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

    # 剩余名额
    beijing_remaining_quota = models.IntegerField(default=0, verbose_name="北京剩余名额")
    yantai_remaining_quota = models.IntegerField(default=0, verbose_name="烟台剩余名额")

    # 总招生名额
    total_quota = models.IntegerField(default=0, verbose_name="硕士总招生名额")

    def save(self, *args, **kwargs):
        """保存时自动计算总数并同步剩余名额。"""
        if self.pk:
            old = ProfessorMasterQuota.objects.get(pk=self.pk)

            # 如果用户没有手动修改剩余名额，则自动调整
            if self.beijing_remaining_quota == old.beijing_remaining_quota:
                bj_diff = (self.beijing_quota or 0) - (old.beijing_quota or 0)
                self.beijing_remaining_quota = max(0, (old.beijing_remaining_quota or 0) + bj_diff)

            if self.yantai_remaining_quota == old.yantai_remaining_quota:
                yt_diff = (self.yantai_quota or 0) - (old.yantai_quota or 0)
                self.yantai_remaining_quota = max(0, (old.yantai_remaining_quota or 0) + yt_diff)
        else:
            # 新建时：剩余 = 可用
            self.beijing_remaining_quota = self.beijing_quota
            self.yantai_remaining_quota = self.yantai_quota

        # 自动计算总数
        self.total_quota = (self.beijing_quota or 0) + (self.yantai_quota or 0)

        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "导师硕士专业名额"
        verbose_name_plural = "导师硕士专业名额"
        unique_together = [['professor', 'subject']]

    def __str__(self):
        prof_name = self.professor.name if self.professor_id else "未绑定导师"
        subj_name = self.subject.subject_name if self.subject_id else "未绑定专业"
        return f"{prof_name} - {subj_name} (总额:{self.total_quota}, 北京剩余={self.beijing_remaining_quota}, 烟台剩余={self.yantai_remaining_quota})"


# ========== 信号：新增硕士专业时，自动初始化导师硕士名额 ==========
# @receiver(post_save, sender=Professor)
@receiver(post_save, sender=Subject)
def initialize_master_quotas(sender, instance, created, **kwargs):
    """当新增硕士专业时，自动为所有导师创建对应的硕士配额记录。"""
    if created and instance.subject_type in [0, 1]:  # 限制为硕士专业
        professors = Professor.objects.all()
        for professor in professors:
            ProfessorMasterQuota.objects.get_or_create(
                professor=professor,
                subject=instance,
                defaults={
                    'beijing_quota': 0,
                    'yantai_quota': 0,
                    'beijing_remaining_quota': 0,
                    'yantai_remaining_quota': 0,
                    'total_quota': 0
                }
            )

# -------- 1) 修复：硕士总指标（按方向）自动汇总 --------
@receiver(post_save, sender=ProfessorMasterQuota)
@receiver(post_delete, sender=ProfessorMasterQuota)
def update_department_master_totals(sender, instance, **kwargs):
    """当硕士配额变化时，汇总所在方向的硕士总指标。"""
    dept = getattr(instance.professor, "department", None)
    if not dept:
        return

    qs = ProfessorMasterQuota.objects.filter(professor__department=dept)

    # 学硕 = subject_type=1，对应北京名额
    academic_bj = qs.filter(subject__subject_type=1).aggregate(
        s=Coalesce(Sum('beijing_quota'), 0)
    )['s']

    # 专硕 = subject_type=0，对应北京和烟台名额
    prof_bj = qs.filter(subject__subject_type=0).aggregate(
        s=Coalesce(Sum('beijing_quota'), 0)
    )['s']
    prof_yt = qs.filter(subject__subject_type=0).aggregate(
        s=Coalesce(Sum('yantai_quota'), 0)
    )['s']

    dept.total_academic_quota = academic_bj
    dept.total_professional_quota = prof_bj
    dept.total_professional_yt_quota = prof_yt
    dept.save(update_fields=[
        'total_academic_quota',
        'total_professional_quota',
        'total_professional_yt_quota'
    ])


# -------- 2) 修复：博士总指标自动汇总 --------
@receiver(post_save, sender=ProfessorDoctorQuota)
@receiver(post_delete, sender=ProfessorDoctorQuota)
def update_department_doctor_totals(sender, instance, **kwargs):
    """任意博士配额变动后，汇总所在方向的博士总指标。"""
    dept = getattr(instance.professor, "department", None)
    if not dept:
        return

    total_doc = ProfessorDoctorQuota.objects.filter(
        professor__department=dept
    ).aggregate(s=Coalesce(Sum('total_quota'), 0))['s']

    dept.total_doctor_quota = total_doc
    dept.save(update_fields=['total_doctor_quota'])


@receiver(post_save, sender=ProfessorSharedQuotaPool)
@receiver(post_delete, sender=ProfessorSharedQuotaPool)
def refresh_professor_summary_for_shared_pool(sender, instance, **kwargs):
    recalculate_professor_quota_summary(instance.professor)


def get_default_admission_year():
    today = timezone.localdate()
    return today.year + 1 if (today.month, today.day) >= (9, 1) else today.year


class AdmissionBatch(models.Model):
    name = models.CharField(max_length=100, verbose_name="批次名称")
    admission_year = models.PositiveIntegerField(default=get_default_admission_year, verbose_name="届别")
    batch_code = models.CharField(max_length=50, blank=True, default="", verbose_name="批次编码")
    sort_order = models.IntegerField(default=0, verbose_name="排序值")
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    description = models.TextField(blank=True, default="", verbose_name="批次说明")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        verbose_name = "招生批次"
        verbose_name_plural = "招生批次"
        ordering = ['-admission_year', 'sort_order', 'id']
        unique_together = [['admission_year', 'name']]

    def __str__(self):
        return f"{self.admission_year}届 - {self.name}"


class Student(models.Model):
    # 用户名
    user_name = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100, verbose_name="学生姓名")
    name_fk_search = models.CharField(max_length=100, verbose_name="学生(搜索专用)", null=True)
    candidate_number = models.CharField(max_length=20, unique=True, verbose_name="考生编号")
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
    is_signate_giveup_table = models.BooleanField(default=False, verbose_name="是否签名放弃说明表")
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
    # 综合排名
    final_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="综合排名")
    # 候补状态
    is_alternate = models.BooleanField(default=False, verbose_name="是否候补")
    alternate_rank = models.PositiveIntegerField(null=True, blank=True, verbose_name="候补顺序")

    admission_year = models.PositiveIntegerField(default=get_default_admission_year, verbose_name="届别")
    admission_batch = models.ForeignKey(
        AdmissionBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='students',
        verbose_name="招生批次",
    )
    can_login = models.BooleanField(default=True, verbose_name="允许登录小程序")
    selection_display_enabled = models.BooleanField(default=True, verbose_name="允许显示在可选学生池")

    class Meta:
        verbose_name = "学生"  # 设置模型的显示名称
        verbose_name_plural = "学生"  # 设置模型的复数显示名称

    def save(self, *args, **kwargs):
        self.name_fk_search = self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
        return self.name


@receiver(pre_save, sender=Student)
def cache_student_login_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._old_can_login = None
        return
    old_student = Student.objects.filter(pk=instance.pk).only('can_login').first()
    instance._old_can_login = old_student.can_login if old_student else None


@receiver(post_save, sender=Student)
def revoke_student_tokens_when_login_disabled(sender, instance, **kwargs):
    old_can_login = getattr(instance, '_old_can_login', None)
    if instance.user_name_id and old_can_login is True and instance.can_login is False:
        Token.objects.filter(user=instance.user_name).delete()
        WeChatAccount.objects.filter(user=instance.user_name).delete()

