from rest_framework import serializers
from Professor_Student_Manage.models import Professor, Student, Department
from django.contrib.auth.models import User


class StudentSerializer(serializers.ModelSerializer):
    
    subject = serializers.SlugRelatedField(
        read_only=True,
        slug_field='subject_name'
     )

    class Meta:
        model = Student
        fields = '__all__'  # 或者指定您想要序列化的字段

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


class ProfessorSerializer(serializers.ModelSerializer):
    enroll_subject = serializers.StringRelatedField(many=True)
    
    class Meta:
        model = Professor
        # print()
        fields = [f.name for f in Professor._meta.get_fields() if f.name != 'enroll_subject' and f.name != 'studentprofessorchoice'] + ['enroll_subject']



class ProfessorListSerializer(serializers.ModelSerializer):
    enroll_subject = serializers.StringRelatedField(many=True)
    
    class Meta:
        model = Professor
        # print()
        fields = [f.name for f in Professor._meta.get_fields() if f.name != 'enroll_subject' and f.name != 'studentprofessorchoice'] + ['enroll_subject']

    def to_representation(self, instance):
        """
        重写序列化输出，将 professional_quota 转换为"有"/"无"
        """
        data = super().to_representation(instance)
        data['professional_quota'] = "有" if instance.professional_quota != 0 else "无"
        data['academic_quota'] = "有" if instance.academic_quota != 0 else "无"
        data['professional_yt_quota'] = "有" if instance.professional_yt_quota != 0 else "无"
        data['doctor_quota'] = "有" if instance.doctor_quota != 0 else "无"

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