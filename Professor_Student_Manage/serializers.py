from rest_framework import serializers
from Professor_Student_Manage.models import (
    Professor,
    get_professor_heat_display_metrics,
    get_professor_heat_display_setting,
    ProfessorHeatDisplaySetting,
    ProfessorProfileSection,
    Student,
    Department,
    ProfessorDoctorQuota,
    ProfessorSharedQuotaPool,
)
from django.contrib.auth.models import User
from Enrollment_Manage.models import Subject
from django.db import models


def _get_prefetched_related_list(instance, relation_name):
    cache = getattr(instance, '_prefetched_objects_cache', {})
    if relation_name in cache:
        return list(cache[relation_name])
    return list(getattr(instance, relation_name).all())


def _get_sorted_profile_sections(instance):
    sections = _get_prefetched_related_list(instance, 'profile_sections')
    return sorted(
        [section for section in sections if getattr(section, 'is_active', True)],
        key=lambda section: (section.sort_order or 0, section.id or 0),
    )


def _get_sorted_shared_pools(instance, remaining_only=False):
    pools = _get_prefetched_related_list(instance, 'shared_quota_pools')
    filtered = [
        pool for pool in pools
        if getattr(pool, 'is_active', False) and (not remaining_only or (pool.remaining_quota or 0) > 0)
    ]
    return sorted(
        filtered,
        key=lambda pool: (pool.quota_scope or '', pool.campus or '', pool.id or 0),
    )


def _get_pool_subjects(pool):
    cache = getattr(pool, '_prefetched_objects_cache', {})
    if 'subjects' in cache:
        return list(cache['subjects'])
    return list(pool.subjects.all())


def _get_cached_master_quotas(instance):
    return _get_prefetched_related_list(instance, 'master_quotas')


def _get_cached_doctor_quotas(instance):
    return _get_prefetched_related_list(instance, 'doctor_quotas')


def _get_subject_type_set(subjects):
    return {subject.subject_type for subject in subjects}


def _calculate_professor_quota_counts(instance):
    academic_quota_count = 0
    professional_quota_count = 0
    professional_yt_quota_count = 0
    doctor_quota_count = 0

    for quota in _get_cached_master_quotas(instance):
        if quota.subject.subject_type == 1:
            academic_quota_count += quota.beijing_remaining_quota or 0
        elif quota.subject.subject_type == 0:
            professional_quota_count += quota.beijing_remaining_quota or 0
            professional_yt_quota_count += quota.yantai_remaining_quota or 0

    for quota in _get_cached_doctor_quotas(instance):
        if quota.subject.subject_type == 2:
            doctor_quota_count += quota.remaining_quota or 0

    for pool in _get_sorted_shared_pools(instance, remaining_only=False):
        subjects = _get_pool_subjects(pool)
        subject_types = _get_subject_type_set(subjects)
        remaining_quota = pool.remaining_quota or 0

        if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_DOCTOR:
            if 2 in subject_types:
                doctor_quota_count += remaining_quota
            continue

        if pool.campus == ProfessorSharedQuotaPool.CAMPUS_YANTAI:
            if 0 in subject_types:
                professional_yt_quota_count += remaining_quota
            continue

        if 1 in subject_types:
            academic_quota_count += remaining_quota
        if 0 in subject_types:
            professional_quota_count += remaining_quota

    return {
        'academic_quota_count': academic_quota_count,
        'professional_quota_count': professional_quota_count,
        'professional_yt_quota_count': professional_yt_quota_count,
        'doctor_quota_count': doctor_quota_count,
    }


def build_fixed_quota_sections(instance):
    sections = []
    master_quotas = _get_cached_master_quotas(instance)
    doctor_quotas = _get_cached_doctor_quotas(instance)

    academic_items = [
        {
            'subject_name': quota.subject.subject_name,
            'remaining_quota': quota.beijing_remaining_quota or 0,
            'total_quota': quota.beijing_quota or 0,
        }
        for quota in master_quotas
        if quota.subject.subject_type == 1
        if (quota.beijing_quota or 0) > 0 or (quota.beijing_remaining_quota or 0) > 0
    ]
    if academic_items:
        sections.append({'key': 'academic', 'title': '学硕固定专业名额', 'items': academic_items})

    professional_bj_items = [
        {
            'subject_name': quota.subject.subject_name,
            'remaining_quota': quota.beijing_remaining_quota or 0,
            'total_quota': quota.beijing_quota or 0,
        }
        for quota in master_quotas
        if quota.subject.subject_type == 0
        if (quota.beijing_quota or 0) > 0 or (quota.beijing_remaining_quota or 0) > 0
    ]
    if professional_bj_items:
        sections.append({'key': 'professional_bj', 'title': '北京专硕固定专业名额', 'items': professional_bj_items})

    professional_yt_items = [
        {
            'subject_name': quota.subject.subject_name,
            'remaining_quota': quota.yantai_remaining_quota or 0,
            'total_quota': quota.yantai_quota or 0,
        }
        for quota in master_quotas
        if quota.subject.subject_type == 0
        if (quota.yantai_quota or 0) > 0 or (quota.yantai_remaining_quota or 0) > 0
    ]
    if professional_yt_items:
        sections.append({'key': 'professional_yt', 'title': '烟台专硕固定专业名额', 'items': professional_yt_items})

    doctor_items = [
        {
            'subject_name': quota.subject.subject_name,
            'remaining_quota': quota.remaining_quota or 0,
            'total_quota': quota.total_quota or 0,
        }
        for quota in doctor_quotas
        if quota.subject.subject_type == 2
        if (quota.total_quota or 0) > 0 or (quota.remaining_quota or 0) > 0
    ]
    if doctor_items:
        sections.append({'key': 'doctor', 'title': '博士固定专业名额', 'items': doctor_items})

    return sections


def get_shared_pool_display_title(pool, subjects=None):
    subjects = subjects if subjects is not None else _get_pool_subjects(pool)
    if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_DOCTOR:
        return '博士共享名额'

    subject_types = _get_subject_type_set(subjects)
    if pool.campus == ProfessorSharedQuotaPool.CAMPUS_YANTAI:
        return '烟台专硕共享名额'
    if subject_types == {1}:
        return '学硕共享名额'
    if subject_types == {0}:
        return '北京专硕共享名额'
    return '硕士共享名额'


def build_shared_quota_sections(instance):
    pools = _get_sorted_shared_pools(instance, remaining_only=False)
    sections = []
    for pool in pools:
        subjects = _get_pool_subjects(pool)
        sections.append({
            'title': get_shared_pool_display_title(pool, subjects),
            'remaining_quota': pool.remaining_quota or 0,
            'total_quota': pool.total_quota or 0,
            'subjects': [subject.subject_name for subject in subjects],
        })
    return sections


def build_profile_sections(instance):
    return [
        {
            'id': section.id,
            'title': section.title,
            'content': section.content,
            'sort_order': section.sort_order,
        }
        for section in _get_sorted_profile_sections(instance)
    ]


class StudentSerializer(serializers.ModelSerializer):
    
    subject = serializers.SlugRelatedField(
        read_only=True,
        slug_field='subject_name'
     )

     # 新增字段
    current_alternate_rank = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = '__all__'  # 或者指定您想要序列化的字段
        extra_fields = ['current_alternate_rank']   

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['student_type'] = self._get_student_type_display(instance)
        rep['postgraduate_type'] = self._get_postgraduate_type_display(instance)
        rep['study_mode'] = self._get_study_mode_display(instance)
        return rep

    def _get_student_type_display(self, instance):
        return instance.get_student_type_display()
    
    def _get_postgraduate_type_display(self, instance):
        return instance.get_postgraduate_type_display()
    
    def _get_study_mode_display(self, instance):
        return instance.get_study_mode_display()

    def get_current_alternate_rank(self, obj):
        """
        计算当前候补次序（动态排名）
        优化：优先从 context 中获取预计算的排名，避免 N+1 查询
        """
        if not obj.alternate_rank:  
            return None  # 没有候补顺序的直接返回 None

        # 优先从 context 中获取预计算的排名映射（由 view 层批量计算后传入）
        alternate_rank_map = self.context.get('alternate_rank_map')
        if alternate_rank_map is not None:
            return alternate_rank_map.get(obj.id)

        # 回退：如果 context 中没有预计算数据，则单独查询（兼容单个对象序列化场景）
        same_subject_students = Student.objects.filter(
            subject=obj.subject,
            alternate_rank__isnull=False,
            is_giveup=False
        ).order_by("alternate_rank")

        for idx, student in enumerate(same_subject_students, start=1):
            if student.id == obj.id:
                return idx


class StudentResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['phone_number', 'avatar', 'resume', 'signature_table', 'giveup_signature_table']  # 或者指定您想要序列化的字段


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username')

class ProfessorDoctorQuotaSerializer(serializers.ModelSerializer):
    subject = serializers.PrimaryKeyRelatedField(queryset=Subject.objects.filter(subject_type=2))

    class Meta:
        model = ProfessorDoctorQuota
        fields = ['subject', 'total_quota', 'used_quota', 'remaining_quota']
        read_only_fields = ['used_quota', 'remaining_quota']


class ProfessorSerializer(serializers.ModelSerializer):
    enroll_subject = serializers.StringRelatedField(many=True)
    doctor_quotas = ProfessorDoctorQuotaSerializer(many=True, required=False)
    master_subjects = serializers.SerializerMethodField()
    doctor_subjects = serializers.SerializerMethodField()
    is_reviewer = serializers.SerializerMethodField()
    
    class Meta:
        model = Professor
        # print()
        fields = [f.name for f in Professor._meta.get_fields() if f.name != 'enroll_subject' and f.name != 'studentprofessorchoice'] + ['enroll_subject', 'master_subjects', 'doctor_subjects', 'is_reviewer']

    def update(self, instance, validated_data):
        # 处理博士专业名额的批量更新
        doctor_quotas_data = validated_data.pop('doctor_quotas', None)
        if doctor_quotas_data:
            for quota_data in doctor_quotas_data:
                subject_id = quota_data.get('subject').id
                total_quota = quota_data.get('total_quota', 0)
                ProfessorDoctorQuota.objects.update_or_create(
                    professor=instance,
                    subject_id=subject_id,
                    defaults={'total_quota': total_quota}
                )
        return super().update(instance, validated_data)

    def get_master_subjects(self, instance):
        serializer = ProfessorListSerializer(context=self.context)
        return serializer._get_available_master_subject_names(instance)

    def get_doctor_subjects(self, instance):
        serializer = ProfessorListSerializer(context=self.context)
        return serializer._get_available_doctor_subject_names(instance)

    def get_is_reviewer(self, instance):
        return instance.department_position in [1, 2]

    def to_representation(self, instance):
        """
        输出时增加“有/无”+数量的招生名额统计字段
        """
        data = super().to_representation(instance)
        quota_counts = _calculate_professor_quota_counts(instance)
        academic_quota_count = quota_counts['academic_quota_count']
        professional_quota_count = quota_counts['professional_quota_count']
        professional_yt_quota_count = quota_counts['professional_yt_quota_count']
        doctor_quota_count = quota_counts['doctor_quota_count']

        # 有/无 + 数量
        data['academic_quota'] = "有" if academic_quota_count > 0 else "无"
        data['academic_quota_count'] = academic_quota_count

        data['professional_quota'] = "有" if professional_quota_count > 0 else "无"
        data['professional_quota_count'] = professional_quota_count

        data['professional_yt_quota'] = "有" if professional_yt_quota_count > 0 else "无"
        data['professional_yt_quota_count'] = professional_yt_quota_count

        data['doctor_quota'] = "有" if doctor_quota_count > 0 else "无"
        data['doctor_quota_count'] = doctor_quota_count
        data['fixed_quota_sections'] = build_fixed_quota_sections(instance)
        data['shared_quota_sections'] = build_shared_quota_sections(instance)
        data['profile_sections'] = build_profile_sections(instance)

        return data


class ProfessorListSerializer(serializers.ModelSerializer):
    # 硕士招生专业
    enroll_subject = serializers.StringRelatedField(many=True)
    master_subjects = serializers.SerializerMethodField()
    # 博士招生专业
    doctor_subjects = serializers.SerializerMethodField()
    heat_score = serializers.SerializerMethodField()
    heat_level = serializers.SerializerMethodField()
    heat_visible = serializers.SerializerMethodField()
    
    class Meta:
        model = Professor
        # print()
        fields = [f.name for f in Professor._meta.get_fields() if f.name != 'enroll_subject' and f.name != 'studentprofessorchoice'] + ['enroll_subject', 'master_subjects', 'doctor_subjects', 'heat_score', 'heat_level', 'heat_visible']

    def _get_active_shared_pools(self, instance):
        return _get_sorted_shared_pools(instance, remaining_only=True)

    def _get_available_master_subject_names(self, instance):
        subject_names = set()
        fixed_master_quotas = _get_cached_master_quotas(instance)
        for quota in fixed_master_quotas:
            if quota.subject.subject_type not in [0, 1]:
                continue
            if (quota.subject.subject_type == 1 and quota.beijing_remaining_quota > 0) or (
                quota.subject.subject_type == 0 and (
                    quota.beijing_remaining_quota > 0 or quota.yantai_remaining_quota > 0
                )
            ):
                subject_names.add(quota.subject.subject_name)

        shared_master_pools = [
            pool for pool in self._get_active_shared_pools(instance)
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER
        ]
        for pool in shared_master_pools:
            if pool.campus == ProfessorSharedQuotaPool.CAMPUS_BEIJING:
                valid_subjects = [subject for subject in _get_pool_subjects(pool) if subject.subject_type in [0, 1]]
            elif pool.campus == ProfessorSharedQuotaPool.CAMPUS_YANTAI:
                valid_subjects = [subject for subject in _get_pool_subjects(pool) if subject.subject_type == 0]
            else:
                valid_subjects = [subject for subject in _get_pool_subjects(pool) if subject.subject_type in [0, 1]]

            for subject in valid_subjects:
                subject_names.add(subject.subject_name)

        return sorted(subject_names)

    def _get_available_doctor_subject_names(self, instance):
        subject_names = set()

        fixed_doctor_quotas = [
            quota for quota in _get_cached_doctor_quotas(instance)
            if quota.subject.subject_type == 2 and (quota.remaining_quota or 0) > 0
        ]
        for quota in fixed_doctor_quotas:
            subject_names.add(quota.subject.subject_name)

        shared_doctor_pools = [
            pool for pool in self._get_active_shared_pools(instance)
            if pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_DOCTOR
        ]
        for pool in shared_doctor_pools:
            for subject in _get_pool_subjects(pool):
                if subject.subject_type != 2:
                    continue
                subject_names.add(subject.subject_name)

        return sorted(subject_names)

    def _get_quota_status_summary(self, instance):
        master_quotas = _get_cached_master_quotas(instance)
        doctor_quotas = _get_cached_doctor_quotas(instance)
        active_shared_pools = self._get_active_shared_pools(instance)

        academic_has_fixed = any(
            quota.subject.subject_type == 1 and (quota.beijing_remaining_quota or 0) > 0
            for quota in master_quotas
        )
        academic_has_shared = any(
            pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER and
            pool.campus == ProfessorSharedQuotaPool.CAMPUS_BEIJING and
            any(subject.subject_type == 1 for subject in _get_pool_subjects(pool))
            for pool in active_shared_pools
        )

        professional_bj_has_fixed = any(
            quota.subject.subject_type == 0 and (quota.beijing_remaining_quota or 0) > 0
            for quota in master_quotas
        )
        professional_bj_has_shared = any(
            pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER and
            pool.campus == ProfessorSharedQuotaPool.CAMPUS_BEIJING and
            any(subject.subject_type == 0 for subject in _get_pool_subjects(pool))
            for pool in active_shared_pools
        )

        professional_yt_has_fixed = any(
            quota.subject.subject_type == 0 and (quota.yantai_remaining_quota or 0) > 0
            for quota in master_quotas
        )
        professional_yt_has_shared = any(
            pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_MASTER and
            pool.campus == ProfessorSharedQuotaPool.CAMPUS_YANTAI and
            any(subject.subject_type == 0 for subject in _get_pool_subjects(pool))
            for pool in active_shared_pools
        )

        doctor_has_fixed = any(
            quota.subject.subject_type == 2 and (quota.remaining_quota or 0) > 0
            for quota in doctor_quotas
        )
        doctor_has_shared = any(
            pool.quota_scope == ProfessorSharedQuotaPool.SCOPE_DOCTOR and
            any(subject.subject_type == 2 for subject in _get_pool_subjects(pool))
            for pool in active_shared_pools
        )

        return {
            'academic_quota': "有" if (academic_has_fixed or academic_has_shared) else "无",
            'professional_quota': "有" if (professional_bj_has_fixed or professional_bj_has_shared) else "无",
            'professional_yt_quota': "有" if (professional_yt_has_fixed or professional_yt_has_shared) else "无",
            'doctor_quota': "有" if (doctor_has_fixed or doctor_has_shared) else "无",
        }

    def get_doctor_subjects(self, instance):
        return self._get_available_doctor_subject_names(instance)

    def _get_heat_metrics(self, instance):
        setting = self.context.get('heat_setting') or get_professor_heat_display_setting()
        subject = self.context.get('heat_subject')
        postgraduate_type = self.context.get('heat_postgraduate_type')
        cache_key = (
            getattr(setting, 'calculation_scope', ProfessorHeatDisplaySetting.CALCULATION_SCOPE_OVERALL),
            getattr(subject, 'id', subject),
            postgraduate_type,
        )
        cache_map = getattr(instance, '_heat_metrics_cache_map', {})
        if cache_key not in cache_map:
            cache_map[cache_key] = get_professor_heat_display_metrics(
                instance,
                global_setting=setting,
                subject=subject,
                postgraduate_type=postgraduate_type,
            )
            instance._heat_metrics_cache_map = cache_map
        return cache_map[cache_key]

    def get_master_subjects(self, instance):
        return self._get_available_master_subject_names(instance)

    def get_heat_score(self, instance):
        return self._get_heat_metrics(instance)['heat_score']

    def get_heat_level(self, instance):
        return self._get_heat_metrics(instance)['heat_level']

    def get_heat_visible(self, instance):
        return self._get_heat_metrics(instance)['heat_visible']

    def to_representation(self, instance):
        """
        重写序列化输出，将 professional_quota 转换为"有"/"无"
        """
        data = super().to_representation(instance)

        # # 学硕（北京）：subject_type=1
        # has_academic_quota = instance.master_quotas.filter(
        #     subject__subject_type=1, beijing_remaining_quota__gt=0
        # ).exists()

        # # 北京专硕：subject_type=0 & 北京名额
        # has_professional_bj_quota = instance.master_quotas.filter(
        #     subject__subject_type=0, beijing_remaining_quota__gt=0
        # ).exists()

        # # 烟台专硕：subject_type=0 & 烟台名额
        # has_professional_yt_quota = instance.master_quotas.filter(
        #     subject__subject_type=0, yantai_remaining_quota__gt=0
        # ).exists()

        # # 博士：保持不变
        # has_doctor_quota = instance.doctor_quotas.filter(
        #     subject__subject_type=2, remaining_quota__gt=0
        # ).exists()

        data.update(self._get_quota_status_summary(instance))

        return data

class ProfessorEnrollInfoSerializer(serializers.ModelSerializer):
    # department = serializers.StringRelatedField()
    # enroll_subject = serializers.StringRelatedField(many=True)

    class Meta:
        model = Professor
        fields = ['name', 'enroll_subject', 'academic_quota', 'professional_quota', 'professional_yt_quota', 'doctor_quota']


class ProfessorPartialUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Professor
        fields = ['email', 'research_areas', 'personal_page', 'avatar', 'contact_details', 'signature_temp']  # 允许修改的字段


class StudentPartialUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['phone_number', 'avatar', 'resume', 'signature_temp']  # 允许修改的字段


class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    password = serializers.CharField(write_only=True)


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = '__all__'  # 或者指定您想要序列化的字段

class DepartmentReviewerSerializer(serializers.ModelSerializer):
    reviewers = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = ['id', 'department_name', 'reviewers']

    def get_reviewers(self, obj):
        # 优先使用 view 层预加载的 reviewer_professors（避免 N+1）
        if hasattr(obj, 'reviewer_professors'):
            reviewers = obj.reviewer_professors
        else:
            reviewers = Professor.objects.filter(department=obj, department_position__in=[1, 2])
        return ProfessorSerializer(reviewers, many=True).data
