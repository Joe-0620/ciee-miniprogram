from rest_framework import serializers
from Professor_Student_Manage.models import Professor, Student
from Select_Information.models import StudentProfessorChoice, SelectionTime
from django.contrib.auth.models import User
from .models import ReviewRecord


class SelectionTimeSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SelectionTime
        fields = '__all__'  # 或者指定您想要序列化的字段

class StudentProfessorChoiceSerializer(serializers.ModelSerializer):
    student = serializers.CharField(source='student.name')
    student_subject = serializers.CharField(source='student.subject')
    student_type = serializers.CharField(source='student.student_type')
    student_postgraduate_type = serializers.CharField(source='student.postgraduate_type')
    student_id = serializers.CharField(source='student.id')
    professor_id = serializers.CharField(source='professor.id')
    professor_avatar = serializers.CharField(source='professor.avatar')
    professor = serializers.CharField(source='professor.name')
    professor_department = serializers.CharField(source='professor.department')
    professor_contact_details = serializers.CharField(source='professor.contact_details')
    student_avatar = serializers.CharField(source='student.avatar')
    student_phone = serializers.CharField(source='student.phone_number')
    student_initial_exam_score = serializers.CharField(source='student.initial_exam_score')
    student_secondary_exam_score = serializers.CharField(source='student.secondary_exam_score')
    student_initial_rank = serializers.CharField(source='student.initial_rank')
    student_secondary_rank = serializers.CharField(source='student.secondary_rank')
    student_final_rank = serializers.CharField(source='student.final_rank')
    student_pdf_file_id = serializers.CharField(source='student.signature_table')
    student_signature_table_review_status = serializers.CharField(source='student.signature_table_review_status')
    # student_final_rank = serializers.CharField(source='student.final_rank')
    signature_table_review_status = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfessorChoice
        # fields = '__all__'  # 或者指定您想要序列化的字段
        fields = ['student', 'student_subject', 'student_type', 'student_postgraduate_type', 'student_id', 'professor_avatar',
                  'professor', 'professor_id', 'professor_department', 'status', 'chosen_by_professor', 'submit_date', 
                  'finish_time', 'student_phone', 'student_avatar', 'student_initial_exam_score', 'student_secondary_exam_score',
                  'student_initial_rank', 'student_secondary_rank', 'student_final_rank', 'professor_contact_details', 'student_pdf_file_id',
                  'signature_table_review_status']

    def get_student_signature_table_review_status_display(self, obj):
        REVIEW_STATUS = [
            [1, "已同意"],
            [2, "已拒绝"],
            [3, "待审核"],
            [4, "未提交"]
        ]
        return dict(REVIEW_STATUS).get(obj.student.signature_table_review_status, '未知类型')

    def get_student_name(self, obj):
        return obj.student.name

    def get_professor_name(self, obj):
        return obj.professor.name
    

class ReviewRecordSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    professor_name = serializers.CharField(source='professor.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True)
    reviewer_name = serializers.CharField(source='reviewer.name', read_only=True)
    student_subject = serializers.CharField(source='student.subject', read_only=True)
    student_type = serializers.CharField(source='student.student_type', read_only=True)
    student_postgraduate_type = serializers.CharField(source='student.postgraduate_type', read_only=True)
    student_postgraduate_type_display = serializers.SerializerMethodField()
    student_type_display = serializers.SerializerMethodField()

    class Meta:
        model = ReviewRecord
        fields = ['id', 'student_name', 'professor_name', 'file_id', 'status', 'review_status', 'review_time', 
                  'reviewer_name', 'student_subject', 'student_type', 'student_postgraduate_type', 
                  'student_postgraduate_type_display', 'student_type_display', 'submit_time']
        
    def get_student_postgraduate_type_display(self, obj):
        BACHELOR_TYPE = [
            [1, "专业型(北京)"],
            [2, "学术型"],
            [3, "博士"],
            [4, "专业型(烟台)"],
        ]
        return dict(BACHELOR_TYPE).get(obj.student.postgraduate_type, '未知类型')
    
    def get_student_type_display(self, obj):
        STUDENT_CHOICES = [
            [1, "硕士推免生"],
            [2, "硕士统考生"],
            [3, "博士统考生"],
        ]
        return dict(STUDENT_CHOICES).get(obj.student.student_type, '未知类型')
    
class ReviewRecordUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewRecord
        fields = ['review_status', 'status']