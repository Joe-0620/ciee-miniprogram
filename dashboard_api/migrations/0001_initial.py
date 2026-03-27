from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operator_username', models.CharField(blank=True, default='', max_length=150, verbose_name='操作管理员用户名')),
                ('action', models.CharField(max_length=100, verbose_name='操作动作')),
                ('module', models.CharField(max_length=100, verbose_name='所属模块')),
                ('level', models.CharField(choices=[('info', '信息'), ('warning', '警告'), ('error', '错误')], default='info', max_length=20, verbose_name='风险级别')),
                ('status', models.CharField(choices=[('success', '成功'), ('failed', '失败')], default='success', max_length=20, verbose_name='执行结果')),
                ('target_type', models.CharField(blank=True, default='', max_length=100, verbose_name='对象类型')),
                ('target_id', models.CharField(blank=True, default='', max_length=100, verbose_name='对象 ID')),
                ('target_display', models.CharField(blank=True, default='', max_length=255, verbose_name='对象名称')),
                ('detail', models.TextField(blank=True, default='', verbose_name='详细说明')),
                ('before_data', models.JSONField(blank=True, null=True, verbose_name='变更前数据')),
                ('after_data', models.JSONField(blank=True, null=True, verbose_name='变更后数据')),
                ('request_method', models.CharField(blank=True, default='', max_length=16, verbose_name='请求方法')),
                ('request_path', models.CharField(blank=True, default='', max_length=255, verbose_name='请求路径')),
                ('ip_address', models.CharField(blank=True, default='', max_length=64, verbose_name='IP 地址')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='客户端信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dashboard_audit_logs', to=settings.AUTH_USER_MODEL, verbose_name='操作管理员')),
            ],
            options={
                'verbose_name': '后台操作审计日志',
                'verbose_name_plural': '后台操作审计日志',
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='dashboardauditlog',
            index=models.Index(fields=['-created_at'], name='dashboard_a_created_21895d_idx'),
        ),
        migrations.AddIndex(
            model_name='dashboardauditlog',
            index=models.Index(fields=['module', 'action'], name='dashboard_a_module_0307d8_idx'),
        ),
        migrations.AddIndex(
            model_name='dashboardauditlog',
            index=models.Index(fields=['status', 'level'], name='dashboard_a_status_b57ea4_idx'),
        ),
    ]
