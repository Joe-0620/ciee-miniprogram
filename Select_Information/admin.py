from django.contrib import admin

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

class SelectionTimeAdmin(admin.ModelAdmin):
    fieldsets = [
        ("互选信息更改", {"fields": ["open_time", "close_time"]}),
    ]
    list_display = ["open_time", "close_time"]

class ReviewRecordAdmin(admin.ModelAdmin):
    fieldsets = [
        ("审核信息", {"fields": ["student", "professor", "file_id", "review_status", "review_time", "reviewer"]}),
    ]
    list_display = ["student", "professor", "file_id", "review_status", "review_time", "reviewer"]
    search_fields = ["student__name_fk_search", "professor__name_fk_search"]

admin.site.register(ReviewRecord, ReviewRecordAdmin)
admin.site.register(StudentProfessorChoice, StudentProfessorChoiceApprovalAdmin)
admin.site.register(SelectionTime, SelectionTimeAdmin)
