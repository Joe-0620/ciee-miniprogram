# Select_Information/admin
from django.contrib import admin
from django.http import HttpResponse
import csv
import codecs
from django.utils import timezone
from openpyxl import Workbook

# Register your models here.
from .models import StudentProfessorChoice, SelectionTime, ReviewRecord


# ========== 审核记录 ==========
class ReviewRecordAdmin(admin.ModelAdmin):
    fieldsets = [
        ("审核信息", {"fields": ["student", "professor", "file_id", "review_status", "review_time", "reviewer"]}),
    ]
    list_display = ["student", "professor", "status", "review_status", "review_time", "reviewer"]
    search_fields = ["student__name_fk_search", "professor__name_fk_search"]

    actions = ["batch_approve"]

    def batch_approve(self, request, queryset):
        """批量通过待审核的记录（状态=3）"""
        count = 0
        for record in queryset.filter(status=3):
            record.status = 1  # 已通过
            record.review_time = timezone.now()
            record.review_status = False  # 保持 False，区分人工审核
            record.save()
            count += 1
        self.message_user(request, f"成功批量通过 {count} 条待审核记录")
    batch_approve.short_description = "批量通过待审核记录"


# ========== 师生互选 ==========
class StudentProfessorChoiceApprovalAdmin(admin.ModelAdmin):
    fieldsets = [
        ("互选信息更改", {"fields": ["student", "professor", "status", "chosen_by_professor",
                                     "submit_date"]}),
    ]
    list_display = ["student", "professor", "status", "chosen_by_professor", "submit_date",
                    "finish_time"]

    search_fields = ["student__name_fk_search", "professor__name_fk_search"]

    actions = ["export_selected_choices"]

    # def export_selected_choices(self, request, queryset):
    #     """导出状态=已同意 且 是否选中=True 的师生互选记录"""
    #     accepted_choices = StudentProfessorChoice.objects.filter(status=1, chosen_by_professor=True)

    #     response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
    #     response['Content-Disposition'] = 'attachment; filename="%s"' % "师生互选表-已同意选中.csv"

    #     response.write(codecs.BOM_UTF8)  # 解决 Excel 打开乱码
    #     writer = csv.writer(response)

    #     # 写表头
    #     writer.writerow([
    #         '专业代码',
    #         '专业名称',
    #         '考生编号',
    #         '姓名',
    #         '初试成绩',
    #         '复试成绩',
    #         '综合成绩',
    #         '综合排名',
    #         '培养层次',
    #         '培养类型',
    #         '手机号',
    #         '导师',
    #         '招生批次'
    #     ])

    #     # 写数据
    #     for choice in accepted_choices:
    #         student = choice.student
    #         professor = choice.professor

    #         # 培养层次（硕士/博士）
    #         if student.postgraduate_type in [1, 2, 4]:
    #             level = "硕士"
    #         elif student.postgraduate_type == 3:
    #             level = "博士"
    #         else:
    #             level = "未知"

    #         # 培养类型（学术学位/专业学位）
    #         if student.postgraduate_type in [2, 3]:  # 学硕 + 博士
    #             degree_type = "学术学位"
    #         elif student.postgraduate_type in [1, 4]:  # 专硕（北京/烟台）
    #             degree_type = "专业学位"
    #         else:
    #             degree_type = "未知"

    #         writer.writerow([
    #             student.subject.subject_code if student.subject else '',
    #             student.subject.subject_name if student.subject else '',
    #             student.candidate_number,
    #             student.name,
    #             student.initial_exam_score,
    #             student.secondary_exam_score,
    #             getattr(student, "final_score", ''),  # 如果有综合成绩
    #             student.final_rank,
    #             level,
    #             degree_type,
    #             student.phone_number,
    #             professor.name if professor else '',
    #             student.student_type  # 招生批次
    #         ])

    #     return response

    # export_selected_choices.short_description = "导出已同意且选中的师生互选记录"

    def export_selected_choices(self, request, queryset):
        """导出状态=已同意 且 是否选中=True 的师生互选记录 (Excel)"""
        accepted_choices = StudentProfessorChoice.objects.filter(status=1, chosen_by_professor=True)

        # student_type 对应表
        STUDENT_TYPE_MAP = {
            1: "硕士推免生",
            2: "硕士统考生",
            3: "博士统考生",
        }

        # 创建 Excel 工作簿
        wb = Workbook()
        ws = wb.active
        ws.title = "互选结果"

        # 写表头
        headers = [
            '专业代码',
            '专业名称',
            '考生编号',
            '姓名',
            '初试成绩',
            '复试成绩',
            '综合成绩',
            '综合排名',
            '培养层次',
            '培养类型',
            '手机号',
            '导师',
            '招生批次'
        ]
        ws.append(headers)

        # 写数据
        for choice in accepted_choices:
            student = choice.student
            professor = choice.professor

            # 培养层次（硕士/博士）
            if student.postgraduate_type in [1, 2, 4]:
                level = "硕士"
            elif student.postgraduate_type == 3:
                level = "博士"
            else:
                level = "未知"

            # 培养类型（学术学位/专业学位）
            if student.postgraduate_type in [2, 3]:  # 学硕 + 博士
                degree_type = "学术学位"
            elif student.postgraduate_type in [1, 4]:  # 专硕（北京/烟台）
                degree_type = "专业学位"
            else:
                degree_type = "未知"

            # 招生批次（中文映射）
            student_type_display = STUDENT_TYPE_MAP.get(student.student_type, str(student.student_type))

            ws.append([
                student.subject.subject_code if student.subject else '',
                student.subject.subject_name if student.subject else '',
                student.candidate_number,
                student.name,
                student.initial_exam_score,
                student.secondary_exam_score,
                getattr(student, "final_score", ''),  # 如果有综合成绩字段
                student.final_rank,
                level,
                degree_type,
                student.phone_number,
                professor.name if professor else '',
                student_type_display  # 招生批次
            ])

        # 构造响应
        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = 'attachment; filename="师生互选表-已同意选中.xlsx"'

        wb.save(response)
        return response

    export_selected_choices.short_description = "导出已同意且选中的师生互选记录 (Excel)"


class SelectionTimeAdmin(admin.ModelAdmin):
    fieldsets = [
        ("互选信息更改", {"fields": ["open_time", "close_time"]}),
    ]
    list_display = ["open_time", "close_time"]


# 注册
admin.site.register(ReviewRecord, ReviewRecordAdmin)
admin.site.register(StudentProfessorChoice, StudentProfessorChoiceApprovalAdmin)
admin.site.register(SelectionTime, SelectionTimeAdmin)
