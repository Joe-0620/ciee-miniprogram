from django.contrib import admin

# Register your models here.
from .models import StudentProfessorChoice


class StudentProfessorChoiceApprovalAdmin(admin.ModelAdmin):
    fieldsets = [
        ("互选信息更改", {"fields": ["student", "professor", "status", "chosen_by_professor",
                                     "submit_date"]}),
    ]
    list_display = ["student", "professor", "status", "chosen_by_professor", "submit_date",
                    "finish_time"]

    search_fields = ["student__name_fk_search", "professor__name_fk_search"]

admin.site.register(StudentProfessorChoice, StudentProfessorChoiceApprovalAdmin)