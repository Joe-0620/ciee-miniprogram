from rest_framework import serializers
from Professor_Student_Manage.models import Professor, Student
from Select_Information.models import StudentProfessorChoice, SelectionTime
from django.contrib.auth.models import User


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
    # student_final_rank = serializers.CharField(source='student.final_rank')

    class Meta:
        model = StudentProfessorChoice
        # fields = '__all__'  # 或者指定您想要序列化的字段
        fields = ['student', 'student_subject', 'student_type', 'student_postgraduate_type', 'student_id', 'professor_avatar',
                  'professor', 'professor_id', 'professor_department', 'status', 'chosen_by_professor', 'submit_date', 
                  'finish_time', 'student_phone', 'student_avatar', 'student_initial_exam_score', 'student_secondary_exam_score',
                  'student_initial_rank', 'student_secondary_rank', 'student_final_rank', 'professor_contact_details', 'student_pdf_file_id']

    def get_student_name(self, obj):
        return obj.student.name

    def get_professor_name(self, obj):
        return obj.professor.name