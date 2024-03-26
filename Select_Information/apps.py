from django.apps import AppConfig


class SelectInformationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Select_Information"
    verbose_name = '学院师生互选'

    def ready(self):
        import Select_Information.signals  # 激活信号处理器
        # import departments.signals
        from .tasks import request_access_token
        request_access_token()