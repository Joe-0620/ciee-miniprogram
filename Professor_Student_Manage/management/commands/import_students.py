import csv
from django.core.management.base import BaseCommand
from Professor_Student_Manage.models import Student  # 替换成你的学生模型

class Command(BaseCommand):
    help = '批量创建学生'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']

        with open(csv_file_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # 根据 CSV 中的列名访问相应的数据
                name = row['\ufeff姓名']
                # 推免生当作准考证号
                phone_number = row['手机号']
                identify_number = row['身份证号']
                identify_number = str(identify_number).zfill(4)
                student_type = row['学生类型']
                major = row['申请专业']
                major_direction = row['报考专业方向']
                postgraduate_type = row['研究生类型']

                # 创建学生实例并保存到数据库
                student = Student(
                    name=name,
                    candidate_number=phone_number,
                    identify_number=phone_number,
                    major=major,
                    major_direction=major_direction,
                    student_type=student_type,
                    postgraduate_type=postgraduate_type
                )
                student.save()
                self.stdout.write(self.style.SUCCESS(f'成功创建学生: {name}'))