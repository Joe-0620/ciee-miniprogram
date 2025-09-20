from rest_framework import serializers
from Professor_Student_Manage.models import Professor, Student, Department, ProfessorDoctorQuota
from django.contrib.auth.models import User
from Enrollment_Manage.models import Subject
from django.db import models



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
        """
        if not obj.alternate_rank:  
            return None  # 没有候补顺序的直接返回 None

        # 找出同一专业下所有候补生
        same_subject_students = Student.objects.filter(
            subject=obj.subject,
            alternate_rank__isnull=False,
            is_giveup=False  # 可选：排除放弃的
        ).order_by("alternate_rank")

        # 遍历排名，找到当前学生的位置
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
    
    class Meta:
        model = Professor
        # print()
        fields = [f.name for f in Professor._meta.get_fields() if f.name != 'enroll_subject' and f.name != 'studentprofessorchoice'] + ['enroll_subject']

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


class ProfessorListSerializer(serializers.ModelSerializer):
    # 硕士招生专业
    enroll_subject = serializers.StringRelatedField(many=True)
    master_subjects = serializers.SerializerMethodField()
    # 博士招生专业
    doctor_subjects = serializers.SerializerMethodField()
    
    class Meta:
        model = Professor
        # print()
        fields = [f.name for f in Professor._meta.get_fields() if f.name != 'enroll_subject' and f.name != 'studentprofessorchoice'] + ['enroll_subject', 'master_subjects', 'doctor_subjects']

    def get_doctor_subjects(self, instance):
        # 获取导师在博士专业中 total_quota > 0 的专业名称
        doctor_quotas = instance.doctor_quotas.filter(remaining_quota__gt=0, subject__subject_type=2)
        return [quota.subject.subject_name for quota in doctor_quotas]

    def get_master_subjects(self, instance):
        """
        获取导师在硕士专业（学硕/专硕）中有剩余招生名额的专业名称
        """
        master_quotas = instance.master_quotas.filter(
            subject__subject_type__in=[0, 1]  # 0=专硕, 1=学硕
        ).filter(
            models.Q(beijing_remaining_quota__gt=0) | models.Q(yantai_remaining_quota__gt=0)
        )
        return [quota.subject.subject_name for quota in master_quotas]

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

        # 学硕（北京）：subject_type=1
        academic_quota_qs = instance.master_quotas.filter(subject__subject_type=1)
        academic_quota_count = sum(q.beijing_remaining_quota for q in academic_quota_qs)
        has_academic_quota = academic_quota_count > 0

        # 北京专硕：subject_type=0 & 北京名额
        professional_bj_qs = instance.master_quotas.filter(subject__subject_type=0)
        professional_quota_count = sum(q.beijing_remaining_quota for q in professional_bj_qs)
        has_professional_bj_quota = professional_quota_count > 0

        # 烟台专硕：subject_type=0 & 烟台名额
        professional_yt_quota_count = sum(q.yantai_remaining_quota for q in professional_bj_qs)
        has_professional_yt_quota = professional_yt_quota_count > 0

        # 博士：subject_type=2
        doctor_qs = instance.doctor_quotas.filter(subject__subject_type=2)
        doctor_quota_count = sum(q.remaining_quota for q in doctor_qs)
        has_doctor_quota = doctor_quota_count > 0

        # data['academic_quota'] = "有" if has_academic_quota else "无"
        # data['professional_quota'] = "有" if has_professional_bj_quota else "无"
        # data['professional_yt_quota'] = "有" if has_professional_yt_quota else "无"
        # data['doctor_quota'] = "有" if has_doctor_quota else "无"
        # # data['doctor_quota'] = "有" if instance.doctor_quota != 0 else "无"

        # 覆盖输出 “有/无”
        data['academic_quota'] = "有" if has_academic_quota else "无"
        data['professional_quota'] = "有" if has_professional_bj_quota else "无"
        data['professional_yt_quota'] = "有" if has_professional_yt_quota else "无"
        data['doctor_quota'] = "有" if has_doctor_quota else "无"

        # 新增具体数量字段
        data['academic_quota_count'] = academic_quota_count
        data['professional_quota_count'] = professional_quota_count
        data['professional_yt_quota_count'] = professional_yt_quota_count
        data['doctor_quota_count'] = doctor_quota_count

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
        reviewers = Professor.objects.filter(department=obj, department_position__in=[1, 2])
        return ProfessorSerializer(reviewers, many=True).data


