from rest_framework import serializers
from Professor_Student_Manage.models import Professor, Student, Department
from .models import AdmissionQuotaApproval

class AdmissionQuotaApprovalSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source='professor.department')
    professor = serializers.CharField(source='professor.name')

    class Meta:
        model = AdmissionQuotaApproval
        # fields = '__all__'  # 或者指定您想要序列化的字段
        fields = ['id', 'department', 'professor', 'academic_quota', 'professional_quota', 'doctor_quota',
                  'status', 'reviewed_by', 'submit_date', 'reviewed_time']

