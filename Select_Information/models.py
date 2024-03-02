from django.db import models
from Professor_Student_Manage.models import Student, Professor
from django.utils import timezone


class StudentProfessorChoice(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, verbose_name="学生姓名")
    professor = models.ForeignKey(Professor, on_delete=models.CASCADE, verbose_name="导师姓名")

    # ORDER_CHOICES = [
    #     ['1', "第一志愿"],
    #     ['2', "第二志愿"],
    #     ['3', "第三志愿"],
    # ]

    # choice_order = models.CharField(max_length=1, default='1', choices=ORDER_CHOICES, verbose_name="志愿顺序")

    STATUS_CHOICES = [
        ['1', "已同意"],
        ['2', "已拒绝"],
        ['3', "请等待"],
    ]
    status = models.CharField(max_length=1, default='3', choices=STATUS_CHOICES, verbose_name="状态")
    chosen_by_professor = models.BooleanField(default=False, verbose_name="是否选中")

    # 申请时间
    submit_date = models.DateTimeField(default=timezone.now, verbose_name="提交时间")

    # 审核时间
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")

    class Meta:
        verbose_name = "学院师生互选情况"  # 设置模型的显示名称
        verbose_name_plural = "学院师生互选情况"  # 设置模型的复数形式显示名称

    def __str__(self):
        return f"{self.student} - {self.professor}"
