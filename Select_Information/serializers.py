from rest_framework import serializers
from Professor_Student_Manage.models import Professor, Student
from Select_Information.models import StudentProfessorChoice
from django.contrib.auth.models import User


class StudentProfessorChoiceSerializer(serializers.ModelSerializer):
    student = serializers.CharField(source='student.name')
    student_major = serializers.CharField(source='student.major')
    student_type = serializers.CharField(source='student.student_type')
    student_postgraduate_type = serializers.CharField(source='student.postgraduate_type')
    student_id = serializers.CharField(source='student.id')
    professor = serializers.CharField(source='professor.name')
    professor_department = serializers.CharField(source='professor.department')
    student_phone = serializers.CharField(source='student.phone_number')

    class Meta:
        model = StudentProfessorChoice
        # fields = '__all__'  # 或者指定您想要序列化的字段
        fields = ['student', 'student_major', 'student_type', 'student_postgraduate_type', 'student_id', 
                  'professor', 'professor_department', 'status', 'chosen_by_professor', 'submit_date', 
                  'finish_time', 'student_phone']

    def get_student_name(self, obj):
        return obj.student.name

    def get_professor_name(self, obj):
        return obj.professor.name