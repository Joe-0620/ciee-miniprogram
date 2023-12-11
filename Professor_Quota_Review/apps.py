from django.apps import AppConfig


class ProfessorQuotaReviewConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Professor_Quota_Review"
    verbose_name = '学院导师指标审核'

    def ready(self):
        import Professor_Quota_Review.signals  # 激活信号处理器
        # import departments.signals