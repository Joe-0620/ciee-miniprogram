from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from .models import StudentProfessorChoice
from django.db import models

# 创建一个与模型实例删除相关的信号处理器
@receiver(pre_delete, sender=StudentProfessorChoice)
def restore_data(sender, instance, **kwargs):
    # 在删除 StudentProfessorChoice 实例之前，你可以在这里执行数据恢复操作
    # 例如，根据 instance 中的信息来恢复相关 Department 实例的招生指标
    try:
        print("触发删除信号")
        department = instance.professor.department
        student = instance.student
        professor = instance.professor

        if instance.status == '1':
            # print("进入逻辑1")
            # 如果该选择被标记为“已同意”，则恢复相关招生指标
            if student.student_type == '1' or student.student_type == '2':
                # 学硕或专硕
                # print("进入逻辑2")
                if student.postgraduate_type == '1':
                    # print("进入逻辑3")
                    department.used_professional_quota -= 1
                    professor.professional_quota += 1
                elif student.postgraduate_type == '2':
                    # print("进入逻辑4")
                    department.used_academic_quota -= 1
                    professor.academic_quota += 1
            elif student.student_type == '3':
                # 博士
                # print("进入逻辑5")
                department.used_doctor_quota -= 1
                professor.doctor_quota += 1

            # print("准备跳出逻辑1")
            student.is_selected = False

            # 保存 Department 实例以应用更改
            department.save()
            professor.save()
            student.save()
            # print("触发保存")

    except Exception as e:
        # 处理任何可能的异常
        pass