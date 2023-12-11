from django.apps import AppConfig


class ProfessorStudentManageConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Professor_Student_Manage"
    verbose_name = '学院师生管理'

    def ready(self):
        import Professor_Student_Manage.signals  # 激活信号处理器
        # import departments.signals
