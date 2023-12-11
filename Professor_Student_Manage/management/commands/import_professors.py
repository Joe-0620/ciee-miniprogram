import csv
from django.core.management.base import BaseCommand
from Professor_Student_Manage.models import Professor, Department

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
                manager = int(row['方向审核人'])
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
                    department_position=manager,
                    avatar=avatar,
                    research_areas='待导师完善，可先参考学院官网教师主页',
                    personal_page='等待导师完善'
                )
                professor.save()
                self.stdout.write(self.style.SUCCESS(f'导师工号: {word_number}'))
                self.stdout.write(self.style.SUCCESS(f'成功创建导师: {name}'))