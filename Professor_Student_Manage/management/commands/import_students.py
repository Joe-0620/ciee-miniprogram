import csv
from django.core.management.base import BaseCommand
from Professor_Student_Manage.models import Student  # 替换成你的学生模型
from Enrollment_Manage.models import Subject  # 替换成你的专业模型

class Command(BaseCommand):
    help = '批量创建学生'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']

        with open(csv_file_path, 'r' ,encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # 根据 CSV 中的列名访问相应的数据
                name = row['姓名']
                # 推免生当作准考证号
                identify_number = str(int(float(row['考生编号'])))
                identify_number = str(identify_number).zfill(4)
                student_type = int(row['学生类型'])
                postgraduate_type = int(float(row['研究生类型'].strip()))
                initial_exam_score = float(row['初试成绩'])
                secondary_exam_score = float(row['综合成绩'])
                final_rank = int(row['综合排名'])
                subject_code = str(row['专业代码']).zfill(6)
                # 获取或创建对应的 Subject 对象
                subject, created = Subject.objects.get_or_create(subject_code=subject_code)


                # 创建学生实例并保存到数据库
                student = Student(
                    name=name,
                    candidate_number=identify_number,
                    identify_number=identify_number,
                    student_type=student_type,
                    postgraduate_type=postgraduate_type,
                    initial_exam_score=initial_exam_score,
                    secondary_exam_score=secondary_exam_score,
                    final_rank=final_rank,
                    subject=subject
                )


                student.save()
                self.stdout.write(self.style.SUCCESS(f'成功创建学生: {name}'))