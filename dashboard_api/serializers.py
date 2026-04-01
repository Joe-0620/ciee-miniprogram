from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.authtoken.models import Token

from Enrollment_Manage.models import Department, Subject
from Professor_Student_Manage.models import (
    AvailableStudentDisplaySetting,
    AdmissionBatch,
    get_professor_heat_display_metrics,
    Professor,
    ProfessorHeatDisplaySetting,
    ProfessorDoctorQuota,
    ProfessorMasterQuota,
    ProfessorSharedQuotaPool,
    Student,
    WeChatAccount,
)
from Select_Information.models import ReviewRecord, SelectionTime, StudentProfessorChoice
from .models import DashboardAuditLog, DashboardLoginSession


class DashboardAdminSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'last_login', 'is_staff', 'is_superuser', 'display_name']

    def get_display_name(self, obj):
        full_name = f'{obj.first_name} {obj.last_name}'.strip()
        return full_name or obj.username


class DashboardLoginSessionSerializer(serializers.ModelSerializer):
    device_label = serializers.SerializerMethodField()
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = DashboardLoginSession
        fields = [
            'key',
            'ip_address',
            'user_agent',
            'device_label',
            'created_at',
            'last_seen_at',
            'is_active',
            'is_current',
        ]

    def get_device_label(self, obj):
        user_agent = (obj.user_agent or '').lower()
        system = '未知设备'
        browser = ''

        if 'windows' in user_agent:
            system = 'Windows'
        elif 'mac os x' in user_agent or 'macintosh' in user_agent:
            system = 'macOS'
        elif 'android' in user_agent:
            system = 'Android'
        elif 'iphone' in user_agent or 'ipad' in user_agent or 'ios' in user_agent:
            system = 'iOS'
        elif 'linux' in user_agent:
            system = 'Linux'

        if 'edg/' in user_agent:
            browser = 'Edge'
        elif 'chrome/' in user_agent and 'edg/' not in user_agent:
            browser = 'Chrome'
        elif 'firefox/' in user_agent:
            browser = 'Firefox'
        elif 'safari/' in user_agent and 'chrome/' not in user_agent:
            browser = 'Safari'

        return f'{system}{f" · {browser}" if browser else ""}'

    def get_is_current(self, obj):
        current_key = self.context.get('current_session_key')
        return bool(current_key and current_key == obj.key)


class DashboardAuditLogListSerializer(serializers.ModelSerializer):
    operator_display_name = serializers.SerializerMethodField()
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DashboardAuditLog
        fields = [
            'id',
            'operator_id',
            'operator_username',
            'operator_display_name',
            'action',
            'module',
            'level',
            'level_display',
            'status',
            'status_display',
            'target_type',
            'target_id',
            'target_display',
            'detail',
            'request_method',
            'request_path',
            'ip_address',
            'created_at',
        ]

    def get_operator_display_name(self, obj):
        if obj.operator:
            full_name = f'{obj.operator.first_name} {obj.operator.last_name}'.strip()
            return full_name or obj.operator.username
        return obj.operator_username or '匿名管理员'


class DashboardAuditLogDetailSerializer(DashboardAuditLogListSerializer):
    class Meta(DashboardAuditLogListSerializer.Meta):
        fields = DashboardAuditLogListSerializer.Meta.fields + [
            'before_data',
            'after_data',
            'user_agent',
        ]


class DashboardUserSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()
    linked_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id',
            'username',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'date_joined',
            'last_login',
            'display_name',
            'user_type',
            'linked_name',
        ]

    def get_display_name(self, obj):
        full_name = f'{obj.first_name} {obj.last_name}'.strip()
        return full_name or obj.username

    def get_user_type(self, obj):
        if hasattr(obj, 'professor'):
            return '导师'
        if hasattr(obj, 'student'):
            return '学生'
        if obj.is_superuser:
            return '超级管理员'
        if obj.is_staff:
            return '管理员'
        return '普通用户'

    def get_linked_name(self, obj):
        if hasattr(obj, 'professor'):
            return obj.professor.name
        if hasattr(obj, 'student'):
            return obj.student.name
        full_name = f'{obj.first_name} {obj.last_name}'.strip()
        return full_name or None


class DepartmentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'department_name']


class SubjectBriefSerializer(serializers.ModelSerializer):
    subject_type_display = serializers.CharField(source='get_subject_type_display', read_only=True)

    class Meta:
        model = Subject
        fields = ['id', 'subject_name', 'subject_code', 'subject_type', 'subject_type_display']


class AdmissionBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionBatch
        fields = [
            'id',
            'name',
            'admission_year',
            'batch_code',
            'sort_order',
            'is_active',
            'description',
            'created_at',
            'updated_at',
        ]


class AvailableStudentDisplaySettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AvailableStudentDisplaySetting
        fields = [
            'enabled',
            'require_resume',
            'allowed_admission_years',
            'allowed_batch_ids',
            'allowed_postgraduate_types',
            'updated_at',
        ]


class SelectionTimeSerializer(serializers.ModelSerializer):
    status_text = serializers.SerializerMethodField()
    target_display = serializers.CharField(source='get_target_display', read_only=True)

    class Meta:
        model = SelectionTime
        fields = ['id', 'target', 'target_display', 'open_time', 'close_time', 'status_text']

    def get_status_text(self, obj):
        from django.utils import timezone

        now = timezone.now()
        if obj.open_time and now < obj.open_time:
            return '未开始'
        if obj.close_time and now > obj.close_time:
            return '已结束'
        return '进行中'


class ProfessorListSerializer(serializers.ModelSerializer):
    department = DepartmentBriefSerializer(read_only=True)
    master_subjects = serializers.SerializerMethodField()
    doctor_subjects = serializers.SerializerMethodField()
    shared_quota_pool_count = serializers.SerializerMethodField()
    shared_quota_summary = serializers.SerializerMethodField()
    pending_choice_count = serializers.SerializerMethodField()
    accepted_choice_count = serializers.SerializerMethodField()
    heat_score = serializers.SerializerMethodField()
    heat_level = serializers.SerializerMethodField()
    available_quota_total = serializers.SerializerMethodField()
    heat_visible = serializers.SerializerMethodField()
    heat_display_enabled = serializers.BooleanField(read_only=True)
    manual_heat_score = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True, allow_null=True)
    manual_heat_level = serializers.CharField(read_only=True)

    class Meta:
        model = Professor
        fields = [
            'id',
            'name',
            'teacher_identity_id',
            'professor_title',
            'department',
            'email',
            'phone_number',
            'contact_details',
            'have_qualification',
            'proposed_quota_approved',
            'department_position',
            'remaining_quota',
            'website_order',
            'master_subjects',
            'doctor_subjects',
            'shared_quota_pool_count',
            'shared_quota_summary',
            'pending_choice_count',
            'accepted_choice_count',
            'heat_score',
            'heat_level',
            'available_quota_total',
            'heat_visible',
            'heat_display_enabled',
            'manual_heat_score',
            'manual_heat_level',
        ]

    def _get_heat_metrics(self, obj):
        metrics_map = self.context.get('heat_metrics_map') or {}
        if obj.id in metrics_map:
            return metrics_map[obj.id]
        setting = self.context.get('heat_setting')
        subject = self.context.get('heat_subject')
        postgraduate_type = self.context.get('heat_postgraduate_type')
        student_type = self.context.get('heat_student_type')
        cache_key = (
            ProfessorHeatDisplaySetting.CALCULATION_SCOPE_SUBJECT,
            getattr(subject, 'id', subject),
            postgraduate_type,
            student_type,
            getattr(setting, 'target_admission_year', 2026) if setting else 2026,
        )
        cache_map = getattr(obj, '_heat_metrics_cache_map', {})
        if cache_key not in cache_map:
            cache_map[cache_key] = get_professor_heat_display_metrics(
                obj,
                global_setting=setting,
                subject=subject,
                postgraduate_type=postgraduate_type,
                student_type=student_type,
            )
            obj._heat_metrics_cache_map = cache_map
        return cache_map[cache_key]

    def get_master_subjects(self, obj):
        quotas = getattr(obj, 'master_quotas', None)
        if hasattr(quotas, 'all'):
            quotas = quotas.all()
        if quotas is None:
            quotas = obj.master_quotas.select_related('subject').all()
        return sorted(
            {
                quota.subject.subject_name
                for quota in quotas
                if quota.subject_id and ((quota.beijing_quota or 0) > 0 or (quota.yantai_quota or 0) > 0)
            }
        )

    def get_doctor_subjects(self, obj):
        quotas = getattr(obj, 'doctor_quotas', None)
        if hasattr(quotas, 'all'):
            quotas = quotas.all()
        if quotas is None:
            quotas = obj.doctor_quotas.select_related('subject').all()
        return [quota.subject.subject_name for quota in quotas if quota.subject_id and (quota.total_quota or 0) > 0]

    def get_shared_quota_pool_count(self, obj):
        pools = getattr(obj, 'shared_quota_pools', None)
        if hasattr(pools, 'all'):
            pools = pools.all()
        if pools is None:
            pools = obj.shared_quota_pools.prefetch_related('subjects').all()
        return len([pool for pool in pools if getattr(pool, 'is_active', False)])

    def get_shared_quota_summary(self, obj):
        pools = getattr(obj, 'shared_quota_pools', None)
        if hasattr(pools, 'all'):
            pools = pools.all()
        if pools is None:
            pools = obj.shared_quota_pools.prefetch_related('subjects').all()
        summary = []
        for pool in pools:
            if not getattr(pool, 'is_active', False):
                continue
            subjects = list(pool.subjects.all()) if hasattr(pool, 'subjects') else []
            subject_names = [subject.subject_name for subject in subjects[:3]]
            if len(subjects) > 3:
                subject_names.append(f'等 {len(subjects)} 个专业')
            summary.append({
                'id': pool.id,
                'pool_name': pool.pool_name,
                'quota_scope': pool.quota_scope,
                'quota_scope_display': pool.get_quota_scope_display(),
                'campus': pool.campus,
                'campus_display': pool.get_campus_display(),
                'remaining_quota': pool.remaining_quota,
                'total_quota': pool.total_quota,
                'subject_names': subject_names,
            })
        return summary

    def get_pending_choice_count(self, obj):
        return getattr(obj, 'pending_choice_count', 0)

    def get_accepted_choice_count(self, obj):
        return getattr(obj, 'accepted_choice_count', 0)

    def get_heat_score(self, obj):
        return self._get_heat_metrics(obj)['heat_score']

    def get_heat_level(self, obj):
        return self._get_heat_metrics(obj)['heat_level']

    def get_available_quota_total(self, obj):
        return self._get_heat_metrics(obj)['available_quota_total']

    def get_heat_visible(self, obj):
        return self._get_heat_metrics(obj)['heat_visible']


class ProfessorHeatListSerializer(serializers.ModelSerializer):
    department = DepartmentBriefSerializer(read_only=True)
    available_quota_total = serializers.SerializerMethodField()
    heat_score = serializers.SerializerMethodField()
    heat_level = serializers.SerializerMethodField()
    pending_count = serializers.SerializerMethodField()
    accepted_count = serializers.SerializerMethodField()
    rejected_count = serializers.SerializerMethodField()
    heat_visible = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = [
            'id',
            'name',
            'teacher_identity_id',
            'department',
            'have_qualification',
            'available_quota_total',
            'pending_count',
            'accepted_count',
            'rejected_count',
            'heat_score',
            'heat_level',
            'heat_visible',
            'heat_display_enabled',
            'manual_heat_score',
            'manual_heat_level',
        ]

    def _get_heat_metrics(self, obj):
        metrics_map = self.context.get('heat_metrics_map') or {}
        if obj.id in metrics_map:
            return metrics_map[obj.id]
        setting = self.context.get('heat_setting')
        subject = self.context.get('heat_subject')
        postgraduate_type = self.context.get('heat_postgraduate_type')
        student_type = self.context.get('heat_student_type')
        cache_key = (
            ProfessorHeatDisplaySetting.CALCULATION_SCOPE_SUBJECT,
            getattr(subject, 'id', subject),
            postgraduate_type,
            student_type,
            getattr(setting, 'target_admission_year', 2026) if setting else 2026,
        )
        cache_map = getattr(obj, '_heat_metrics_cache_map', {})
        if cache_key not in cache_map:
            cache_map[cache_key] = get_professor_heat_display_metrics(
                obj,
                global_setting=setting,
                subject=subject,
                postgraduate_type=postgraduate_type,
                student_type=student_type,
            )
            obj._heat_metrics_cache_map = cache_map
        return cache_map[cache_key]

    def get_available_quota_total(self, obj):
        return self._get_heat_metrics(obj)['available_quota_total']

    def get_pending_count(self, obj):
        return self._get_heat_metrics(obj)['pending_count']

    def get_accepted_count(self, obj):
        return self._get_heat_metrics(obj)['accepted_count']

    def get_rejected_count(self, obj):
        return self._get_heat_metrics(obj)['rejected_count']

    def get_heat_score(self, obj):
        return self._get_heat_metrics(obj)['heat_score']

    def get_heat_level(self, obj):
        return self._get_heat_metrics(obj)['heat_level']

    def get_heat_visible(self, obj):
        return self._get_heat_metrics(obj)['heat_visible']


class ProfessorHeatDisplaySettingSerializer(serializers.ModelSerializer):
    calculation_scope_display = serializers.CharField(source='get_calculation_scope_display', read_only=True)

    class Meta:
        model = ProfessorHeatDisplaySetting
        fields = [
            'show_professor_heat',
            'calculation_scope',
            'calculation_scope_display',
            'target_admission_year',
            'medium_threshold',
            'high_threshold',
            'very_high_threshold',
            'medium_ratio_threshold',
            'high_ratio_threshold',
            'very_high_ratio_threshold',
            'updated_at',
        ]


class ProfessorDetailSerializer(serializers.ModelSerializer):
    department = DepartmentBriefSerializer(read_only=True)
    master_quotas = serializers.SerializerMethodField()
    doctor_quotas = serializers.SerializerMethodField()
    shared_quota_pools = serializers.SerializerMethodField()
    pending_choice_count = serializers.SerializerMethodField()
    accepted_choice_count = serializers.SerializerMethodField()

    class Meta:
        model = Professor
        fields = [
            'id',
            'name',
            'teacher_identity_id',
            'professor_title',
            'department',
            'email',
            'phone_number',
            'contact_details',
            'research_areas',
            'personal_page',
            'avatar',
            'have_qualification',
            'proposed_quota_approved',
            'department_position',
            'remaining_quota',
            'website_order',
            'master_quotas',
            'doctor_quotas',
            'shared_quota_pools',
            'pending_choice_count',
            'accepted_choice_count',
        ]

    def get_master_quotas(self, obj):
        quotas = getattr(obj, 'master_quotas', None)
        if hasattr(quotas, 'all'):
            quotas = quotas.all()
        if quotas is None:
            quotas = obj.master_quotas.select_related('subject').all()
        return [
            {
                'subject_id': quota.subject_id,
                'subject_name': quota.subject.subject_name,
                'subject_type': quota.subject.subject_type,
                'beijing_quota': quota.beijing_quota,
                'yantai_quota': quota.yantai_quota,
                'beijing_remaining_quota': quota.beijing_remaining_quota,
                'yantai_remaining_quota': quota.yantai_remaining_quota,
                'total_quota': quota.total_quota,
            }
            for quota in quotas
        ]

    def get_doctor_quotas(self, obj):
        quotas = getattr(obj, 'doctor_quotas', None)
        if hasattr(quotas, 'all'):
            quotas = quotas.all()
        if quotas is None:
            quotas = obj.doctor_quotas.select_related('subject').all()
        return [
            {
                'subject_id': quota.subject_id,
                'subject_name': quota.subject.subject_name,
                'subject_type': quota.subject.subject_type,
                'total_quota': quota.total_quota,
                'used_quota': quota.used_quota,
                'remaining_quota': quota.remaining_quota,
            }
            for quota in quotas
        ]

    def get_shared_quota_pools(self, obj):
        pools = getattr(obj, 'shared_quota_pools', None)
        if hasattr(pools, 'all'):
            pools = pools.all()
        if pools is None:
            pools = obj.shared_quota_pools.prefetch_related('subjects').all()
        return SharedQuotaPoolSerializer(pools, many=True).data

    def get_pending_choice_count(self, obj):
        return getattr(obj, 'pending_choice_count', 0)

    def get_accepted_choice_count(self, obj):
        return getattr(obj, 'accepted_choice_count', 0)


class StudentListSerializer(serializers.ModelSerializer):
    subject = SubjectBriefSerializer(read_only=True)
    admission_batch = AdmissionBatchSerializer(read_only=True)
    current_status = serializers.CharField(read_only=True)
    current_status_display = serializers.SerializerMethodField()
    current_choice_status = serializers.SerializerMethodField()
    selected_professor_name = serializers.SerializerMethodField()
    student_type_display = serializers.CharField(source='get_student_type_display', read_only=True)
    postgraduate_type_display = serializers.CharField(source='get_postgraduate_type_display', read_only=True)

    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'candidate_number',
            'subject',
            'admission_year',
            'admission_batch',
            'can_login',
            'selection_display_enabled',
            'student_type',
            'student_type_display',
            'postgraduate_type',
            'postgraduate_type_display',
            'phone_number',
            'is_selected',
            'is_alternate',
            'alternate_rank',
            'is_giveup',
            'signature_table_review_status',
            'final_rank',
            'initial_rank',
            'secondary_rank',
            'current_status',
            'current_status_display',
            'current_choice_status',
            'selected_professor_name',
            'resume',
            'signature_table',
            'giveup_signature_table',
            'is_signate_giveup_table',
        ]

    def get_current_status_display(self, obj):
        return {
            'selected': '已录取',
            'alternate': '候补中',
            'pending': '待处理',
            'incomplete': '未完成',
            'giveup': '已放弃',
        }.get(getattr(obj, 'current_status', None), '未完成')

    def get_current_choice_status(self, obj):
        choice = getattr(obj, 'latest_choice', None)
        if choice is None:
            choice = obj.studentprofessorchoice_set.select_related('professor').order_by('-submit_date').first()
        if not choice:
            return None
        return {
            1: 'accepted',
            2: 'rejected',
            3: 'pending',
            4: 'cancelled',
            5: 'revoked',
        }.get(choice.status, 'unknown')

    def get_selected_professor_name(self, obj):
        choice = obj.studentprofessorchoice_set.select_related('professor').filter(status=1).order_by('-finish_time', '-submit_date').first()
        return choice.professor.name if choice and choice.professor_id else None


class StudentDetailSerializer(serializers.ModelSerializer):
    subject = SubjectBriefSerializer(read_only=True)
    admission_batch = AdmissionBatchSerializer(read_only=True)
    student_type_display = serializers.CharField(source='get_student_type_display', read_only=True)
    postgraduate_type_display = serializers.CharField(source='get_postgraduate_type_display', read_only=True)
    study_mode_display = serializers.CharField(source='get_study_mode_display', read_only=True)
    current_professor = serializers.SerializerMethodField()
    latest_choice = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'candidate_number',
            'identify_number',
            'subject',
            'admission_year',
            'admission_batch',
            'can_login',
            'selection_display_enabled',
            'student_type',
            'student_type_display',
            'postgraduate_type',
            'postgraduate_type_display',
            'study_mode',
            'study_mode_display',
            'phone_number',
            'avatar',
            'resume',
            'signature_table',
            'giveup_signature_table',
            'signature_table_student_signatured',
            'signature_table_professor_signatured',
            'signature_table_review_status',
            'is_selected',
            'is_alternate',
            'alternate_rank',
            'is_giveup',
            'initial_exam_score',
            'secondary_exam_score',
            'initial_rank',
            'secondary_rank',
            'final_rank',
            'current_professor',
            'latest_choice',
        ]

    def get_current_professor(self, obj):
        choice = obj.studentprofessorchoice_set.select_related('professor').filter(status=1).order_by('-finish_time').first()
        if not choice:
            return None
        return {
            'id': choice.professor_id,
            'name': choice.professor.name,
            'teacher_identity_id': choice.professor.teacher_identity_id,
        }

    def get_latest_choice(self, obj):
        choice = obj.studentprofessorchoice_set.select_related('professor').order_by('-submit_date').first()
        if not choice:
            return None
        return {
            'id': choice.id,
            'professor_id': choice.professor_id,
            'professor_name': choice.professor.name,
            'status': choice.status,
            'submit_date': choice.submit_date,
            'finish_time': choice.finish_time,
        }


class ChoiceListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    candidate_number = serializers.CharField(source='student.candidate_number', read_only=True)
    admission_year = serializers.IntegerField(source='student.admission_year', read_only=True)
    signature_table = serializers.CharField(source='student.signature_table', read_only=True)
    postgraduate_type_display = serializers.SerializerMethodField()
    signature_table_status = serializers.SerializerMethodField()
    student_signature_upload_status = serializers.SerializerMethodField()
    professor_signature_upload_status = serializers.SerializerMethodField()
    student_signature_status = serializers.SerializerMethodField()
    professor_signature_status = serializers.SerializerMethodField()
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    professor_teacher_identity_id = serializers.CharField(source='professor.teacher_identity_id', read_only=True)
    department_name = serializers.CharField(source='professor.department.department_name', read_only=True)
    subject_name = serializers.CharField(source='student.subject.subject_name', read_only=True)

    def get_postgraduate_type_display(self, obj):
        if obj.student_id and obj.student:
            return obj.student.get_postgraduate_type_display()
        return ''

    def get_signature_table_status(self, obj):
        if not obj.student_id or not obj.student:
            return '未生成'
        if obj.student.signature_table:
            return '已生成'
        if obj.status == 1:
            return '缺失'
        return '未生成'

    def get_student_signature_upload_status(self, obj):
        if not obj.student_id or not obj.student:
            return '未上传'
        return '已上传' if obj.student.signature_temp else '未上传'

    def get_professor_signature_upload_status(self, obj):
        if not obj.professor_id or not obj.professor:
            return '未上传'
        return '已上传' if obj.professor.signature_temp else '未上传'

    def get_student_signature_status(self, obj):
        if not obj.student_id or not obj.student:
            return '未签字'
        return '已签字' if obj.student.signature_table_student_signatured else '未签字'

    def get_professor_signature_status(self, obj):
        if not obj.student_id or not obj.student:
            return '未签字'
        return '已签字' if obj.student.signature_table_professor_signatured else '未签字'

    class Meta:
        model = StudentProfessorChoice
        fields = [
            'id',
            'student_id',
            'student_name',
            'candidate_number',
            'admission_year',
            'signature_table',
            'postgraduate_type_display',
            'professor_id',
            'professor_name',
            'professor_teacher_identity_id',
            'department_name',
            'subject_name',
            'signature_table_status',
            'student_signature_upload_status',
            'professor_signature_upload_status',
            'student_signature_status',
            'professor_signature_status',
            'status',
            'chosen_by_professor',
            'submit_date',
            'finish_time',
        ]


class StudentChoiceBehaviorSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    cancel_count = serializers.IntegerField(read_only=True)
    distinct_professor_count = serializers.IntegerField(read_only=True)
    admission_year = serializers.IntegerField(read_only=True)
    student_type_display = serializers.SerializerMethodField()
    current_status = serializers.CharField(read_only=True)
    latest_activity_time = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'candidate_number',
            'admission_year',
            'subject_name',
            'student_type',
            'student_type_display',
            'cancel_count',
            'distinct_professor_count',
            'current_status',
            'latest_activity_time',
        ]

    def get_student_type_display(self, obj):
        return obj.get_student_type_display()

    def get_latest_activity_time(self, obj):
        latest_submit = getattr(obj, 'latest_submit_time', None)
        latest_finish = getattr(obj, 'latest_finish_time', None)
        if latest_submit and latest_finish:
            return latest_submit if latest_submit >= latest_finish else latest_finish
        return latest_finish or latest_submit


class ReviewRecordListSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    candidate_number = serializers.CharField(source='student.candidate_number', read_only=True)
    admission_year = serializers.IntegerField(source='student.admission_year', read_only=True)
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True)
    subject_name = serializers.CharField(source='student.subject.subject_name', read_only=True)

    class Meta:
        model = ReviewRecord
        fields = [
            'id',
            'student_id',
            'student_name',
            'candidate_number',
            'admission_year',
            'professor_id',
            'professor_name',
            'reviewer_id',
            'reviewer_name',
            'subject_name',
            'file_id',
            'status',
            'review_status',
            'submit_time',
            'review_time',
        ]


class ReviewRecordDetailSerializer(serializers.ModelSerializer):
    student = StudentDetailSerializer(read_only=True)
    professor = ProfessorDetailSerializer(read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True)
    admission_year = serializers.IntegerField(source='student.admission_year', read_only=True)

    class Meta:
        model = ReviewRecord
        fields = [
            'id',
            'student',
            'professor',
            'reviewer_id',
            'reviewer_name',
            'admission_year',
            'file_id',
            'status',
            'review_status',
            'submit_time',
            'review_time',
        ]


class DepartmentListSerializer(serializers.ModelSerializer):
    subject_count = serializers.IntegerField(read_only=True)
    reviewer_names = serializers.SerializerMethodField()
    remaining_master_quota = serializers.SerializerMethodField()
    remaining_doctor_quota = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id',
            'department_name',
            'total_academic_quota',
            'total_professional_quota',
            'total_professional_yt_quota',
            'total_doctor_quota',
            'used_academic_quota',
            'used_professional_quota',
            'used_professional_yt_quota',
            'used_doctor_quota',
            'subject_count',
            'reviewer_names',
            'remaining_master_quota',
            'remaining_doctor_quota',
        ]

    def get_reviewer_names(self, obj):
        reviewers = getattr(obj, 'prefetched_reviewers', None)
        if reviewers is None:
            reviewers = obj.professor_set.filter(department_position__in=[1, 2]).only('name', 'department_position')
        reviewer_names = [reviewer.name for reviewer in reviewers if getattr(reviewer, 'name', None)]
        return reviewer_names

    def get_remaining_master_quota(self, obj):
        return (
            (obj.total_academic_quota or 0) - (obj.used_academic_quota or 0)
            + (obj.total_professional_quota or 0) - (obj.used_professional_quota or 0)
            + (obj.total_professional_yt_quota or 0) - (obj.used_professional_yt_quota or 0)
        )

    def get_remaining_doctor_quota(self, obj):
        return (obj.total_doctor_quota or 0) - (obj.used_doctor_quota or 0)


class SubjectListSerializer(serializers.ModelSerializer):
    subject_type_display = serializers.CharField(source='get_subject_type_display', read_only=True)
    departments = serializers.SerializerMethodField()
    student_count = serializers.IntegerField(read_only=True)
    selected_student_count = serializers.IntegerField(read_only=True)
    alternate_student_count = serializers.IntegerField(read_only=True)
    giveup_student_count = serializers.IntegerField(read_only=True)
    assigned_quota_total = serializers.IntegerField(read_only=True)
    shared_quota_pool_count = serializers.IntegerField(read_only=True)
    shared_quota_pool_labels = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = [
            'id',
            'subject_name',
            'subject_code',
            'subject_type',
            'subject_type_display',
            'total_admission_quota',
            'departments',
            'student_count',
            'selected_student_count',
            'alternate_student_count',
            'giveup_student_count',
            'assigned_quota_total',
            'shared_quota_pool_count',
            'shared_quota_pool_labels',
        ]

    def get_departments(self, obj):
        departments = getattr(obj, 'prefetched_departments', None)
        if departments is None:
            departments = obj.subject_department.all()
        return [{'id': department.id, 'department_name': department.department_name} for department in departments]

    def get_shared_quota_pool_labels(self, obj):
        return getattr(obj, 'shared_quota_pool_labels', [])


class AlternateStudentSerializer(serializers.ModelSerializer):
    subject = SubjectBriefSerializer(read_only=True)
    current_professor_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'candidate_number',
            'subject',
            'admission_year',
            'final_rank',
            'alternate_rank',
            'current_professor_name',
            'is_giveup',
        ]

    def get_current_professor_name(self, obj):
        choice = obj.studentprofessorchoice_set.select_related('professor').filter(status=1).order_by('-finish_time').first()
        return choice.professor.name if choice and choice.professor_id else None


class GiveupStudentSerializer(serializers.ModelSerializer):
    subject = SubjectBriefSerializer(read_only=True)
    current_professor_name = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = [
            'id',
            'name',
            'candidate_number',
            'subject',
            'admission_year',
            'final_rank',
            'is_selected',
            'is_signate_giveup_table',
            'giveup_signature_table',
            'current_professor_name',
        ]

    def get_current_professor_name(self, obj):
        choice = obj.studentprofessorchoice_set.select_related('professor').filter(status=1).order_by('-finish_time').first()
        return choice.professor.name if choice and choice.professor_id else None


class ProfessorDoctorQuotaSerializer(serializers.ModelSerializer):
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    teacher_identity_id = serializers.CharField(source='professor.teacher_identity_id', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)

    class Meta:
        model = ProfessorDoctorQuota
        fields = [
            'id',
            'professor_id',
            'professor_name',
            'teacher_identity_id',
            'subject_id',
            'subject_name',
            'subject_code',
            'total_quota',
            'used_quota',
            'remaining_quota',
        ]


class ProfessorMasterQuotaSerializer(serializers.ModelSerializer):
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    teacher_identity_id = serializers.CharField(source='professor.teacher_identity_id', read_only=True)
    subject_name = serializers.CharField(source='subject.subject_name', read_only=True)
    subject_code = serializers.CharField(source='subject.subject_code', read_only=True)
    subject_type_display = serializers.CharField(source='subject.get_subject_type_display', read_only=True)

    class Meta:
        model = ProfessorMasterQuota
        fields = [
            'id',
            'professor_id',
            'professor_name',
            'teacher_identity_id',
            'subject_id',
            'subject_name',
            'subject_code',
            'subject_type_display',
            'beijing_quota',
            'beijing_remaining_quota',
            'yantai_quota',
            'yantai_remaining_quota',
            'total_quota',
        ]


class SharedQuotaPoolSerializer(serializers.ModelSerializer):
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    teacher_identity_id = serializers.CharField(source='professor.teacher_identity_id', read_only=True)
    department_name = serializers.CharField(source='professor.department.department_name', read_only=True)
    quota_scope_display = serializers.CharField(source='get_quota_scope_display', read_only=True)
    campus_display = serializers.CharField(source='get_campus_display', read_only=True)
    subject_ids = serializers.SerializerMethodField()
    subject_labels = serializers.SerializerMethodField()

    class Meta:
        model = ProfessorSharedQuotaPool
        fields = [
            'id',
            'professor_id',
            'professor_name',
            'teacher_identity_id',
            'department_name',
            'pool_name',
            'quota_scope',
            'quota_scope_display',
            'campus',
            'campus_display',
            'total_quota',
            'used_quota',
            'remaining_quota',
            'is_active',
            'notes',
            'subject_ids',
            'subject_labels',
            'created_at',
            'updated_at',
        ]

    def get_subject_ids(self, obj):
        return list(obj.subjects.values_list('id', flat=True))

    def get_subject_labels(self, obj):
        return [
            {
                'id': subject.id,
                'subject_name': subject.subject_name,
                'subject_code': subject.subject_code,
                'subject_type': subject.subject_type,
                'subject_type_display': subject.get_subject_type_display(),
            }
            for subject in obj.subjects.all()
        ]


class WeChatAccountSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_display_name = serializers.SerializerMethodField()

    class Meta:
        model = WeChatAccount
        fields = [
            'id',
            'user_id',
            'username',
            'user_display_name',
            'openid',
            'session_key',
        ]

    def get_user_display_name(self, obj):
        if not obj.user_id:
            return None
        full_name = f'{obj.user.first_name} {obj.user.last_name}'.strip()
        return full_name or obj.user.username


class DashboardTokenSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_display_name = serializers.SerializerMethodField()
    user_type = serializers.SerializerMethodField()

    class Meta:
        model = Token
        fields = [
            'key',
            'user_id',
            'username',
            'user_display_name',
            'user_type',
            'created',
        ]

    def get_user_display_name(self, obj):
        user = obj.user
        if hasattr(user, 'professor'):
            return user.professor.name
        if hasattr(user, 'student'):
            return user.student.name
        full_name = f'{user.first_name} {user.last_name}'.strip()
        return full_name or user.username

    def get_user_type(self, obj):
        user = obj.user
        if hasattr(user, 'professor'):
            return '导师'
        if hasattr(user, 'student'):
            return '学生'
        if user.is_superuser:
            return '超级管理员'
        if user.is_staff:
            return '管理员'
        return '普通用户'
