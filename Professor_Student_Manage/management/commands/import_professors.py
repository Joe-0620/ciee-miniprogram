import csv
from django.core.management.base import BaseCommand
from Professor_Student_Manage.models import Professor, Department
from Enrollment_Manage.models import Subject

class Command(BaseCommand):
    help = '批量创建导师'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file_path = kwargs['csv_file']

        departments = Department.objects.all()
        print(departments)

        with open(csv_file_path, 'r') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                # 根据 CSV 中的列名访问相应的数据
                name = row['\ufeff姓名']
                word_number = row['工号']
                word_number = str(word_number).zfill(5)
                direction = row['招生方向']
                avatar = row['照片下载地址']
                department = None

                if direction == '电气工程':
                    department = departments[0]
                elif direction == '农业工程':
                    department = departments[1]
                elif direction == '计算机学科方向一':
                    department = departments[2]
                elif direction == '计算机学科方向二':
                    department = departments[3]
                elif direction == '计算机学科方向三':
                    department = departments[4]
                elif direction == '计算机学科方向四':
                    department = departments[5]

                

                # 创建导师实例并保存到数据库
                professor = Professor(
                    name=name,
                    teacher_identity_id=word_number,
                    department=department,
                    avatar=avatar,
                    research_areas='待导师完善，可先参考学院官网教师主页',
                    personal_page='等待导师完善',
                    contact_details='暂未设置'
                )
                professor.save()

                # 设置多对多关系
                subjects = Subject.objects.filter(subject_name='计算机科学与技术')
                if subjects.exists():
                    professor.enroll_subject.set(subjects)

                self.stdout.write(self.style.SUCCESS(f'导师工号: {word_number}'))
                self.stdout.write(self.style.SUCCESS(f'成功创建导师: {name}'))