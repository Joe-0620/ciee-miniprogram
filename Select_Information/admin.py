from django.contrib import admin
from django.http import HttpResponse
import csv
import codecs

# Register your models here.
from .models import StudentProfessorChoice, SelectionTime, ReviewRecord


class StudentProfessorChoiceApprovalAdmin(admin.ModelAdmin):
    fieldsets = [
        ("互选信息更改", {"fields": ["student", "professor", "status", "chosen_by_professor",
                                     "submit_date"]}),
    ]
    list_display = ["student", "professor", "status", "chosen_by_professor", "submit_date",
                    "finish_time"]

    search_fields = ["student__name_fk_search", "professor__name_fk_search"]
    # actions = ['export_accepted_choices']

    def export_accepted_choices(self, request, queryset):
        # 只导出状态为"已同意"(status=1)的记录
        accepted_choices = StudentProfessorChoice.objects.filter(status=1)
        
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig',
                                )
        # response['Content-Disposition'] = 'attachment; filename="师生互选表-已同意.csv"'
        # 关键修改：确保文件名正确编码
        response['Content-Disposition'] = 'attachment; filename="%s"' % "师生互选表-已同意.csv"


        # 使用csv.writer写入响应，确保正确处理中文
        response.write(codecs.BOM_UTF8)  # 添加UTF-8 BOM头，解决Excel打开乱码
        writer = csv.writer(response)
        # 写入CSV表头
        writer.writerow([
            '专业代码',
            '专业',
            '考生编号'
            '姓名',
            '初试成绩',
            '复试成绩',
            '综合排名',
            '学生类型',
            '导师',
            '状态', 
            '是否选中', 
            '提交时间', 
            '处理时间'
        ])
        
        # 写入数据行
        for choice in accepted_choices:

            subject_code = choice.student.subject.subject_code
            subject_name = choice.student.subject.subject_name
            print(choice.student.name)

            writer.writerow([
                subject_code,
                subject_name,
                choice.student.candidate_number if choice.student else '',
                choice.student.name if choice.student else '',
                choice.student.initial_exam_score if choice.student else '',
                choice.student.secondary_exam_score if choice.student else '',
                choice.student.final_rank if choice.student else '',
                choice.student.postgraduate_type if choice.student else '',
                choice.professor.name if choice.professor else '',
                choice.get_status_display(),
                '是' if choice.chosen_by_professor else '否',
                choice.submit_date.strftime('%Y-%m-%d %H:%M:%S'),
                choice.finish_time.strftime('%Y-%m-%d %H:%M:%S') if choice.finish_time else ''
            ])

            # break
        
        return response
    
    export_accepted_choices.short_description = "导出已同意的师生互选记录"

class SelectionTimeAdmin(admin.ModelAdmin):
    fieldsets = [
        ("互选信息更改", {"fields": ["open_time", "close_time"]}),
    ]
    list_display = ["open_time", "close_time"]

class ReviewRecordAdmin(admin.ModelAdmin):
    fieldsets = [
        ("审核信息", {"fields": ["student", "professor", "file_id", "review_status", "review_time", "reviewer"]}),
    ]
    list_display = ["student", "professor", "file_id", "status", "review_status", "review_time", "reviewer"]
    search_fields = ["student__name_fk_search", "professor__name_fk_search"]

admin.site.register(ReviewRecord, ReviewRecordAdmin)
admin.site.register(StudentProfessorChoice, StudentProfessorChoiceApprovalAdmin)
admin.site.register(SelectionTime, SelectionTimeAdmin)
