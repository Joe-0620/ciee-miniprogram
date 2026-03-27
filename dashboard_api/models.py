from django.conf import settings
from django.db import models


class DashboardAuditLog(models.Model):
    LEVEL_INFO = 'info'
    LEVEL_WARNING = 'warning'
    LEVEL_ERROR = 'error'
    LEVEL_CHOICES = [
        (LEVEL_INFO, '信息'),
        (LEVEL_WARNING, '警告'),
        (LEVEL_ERROR, '错误'),
    ]

    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_SUCCESS, '成功'),
        (STATUS_FAILED, '失败'),
    ]

    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='dashboard_audit_logs',
        verbose_name='操作管理员',
    )
    operator_username = models.CharField(max_length=150, blank=True, default='', verbose_name='操作管理员用户名')
    action = models.CharField(max_length=100, verbose_name='操作动作')
    module = models.CharField(max_length=100, verbose_name='所属模块')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_INFO, verbose_name='风险级别')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS, verbose_name='执行结果')
    target_type = models.CharField(max_length=100, blank=True, default='', verbose_name='对象类型')
    target_id = models.CharField(max_length=100, blank=True, default='', verbose_name='对象 ID')
    target_display = models.CharField(max_length=255, blank=True, default='', verbose_name='对象名称')
    detail = models.TextField(blank=True, default='', verbose_name='详细说明')
    before_data = models.JSONField(null=True, blank=True, verbose_name='变更前数据')
    after_data = models.JSONField(null=True, blank=True, verbose_name='变更后数据')
    request_method = models.CharField(max_length=16, blank=True, default='', verbose_name='请求方法')
    request_path = models.CharField(max_length=255, blank=True, default='', verbose_name='请求路径')
    ip_address = models.CharField(max_length=64, blank=True, default='', verbose_name='IP 地址')
    user_agent = models.TextField(blank=True, default='', verbose_name='客户端信息')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = '后台操作审计日志'
        verbose_name_plural = '后台操作审计日志'
        indexes = [
            models.Index(fields=['-created_at'], name='dashboard_a_created_21895d_idx'),
            models.Index(fields=['module', 'action'], name='dashboard_a_module_0307d8_idx'),
            models.Index(fields=['status', 'level'], name='dashboard_a_status_b57ea4_idx'),
        ]

    def __str__(self):
        operator = self.operator_username or '匿名管理员'
        return f'{operator} - {self.module} - {self.action}'
