from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

import dashboard_api.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dashboard_api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DashboardLoginSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(default=dashboard_api.models.generate_dashboard_session_key, max_length=40, unique=True, verbose_name='会话令牌')),
                ('ip_address', models.CharField(blank=True, default='', max_length=64, verbose_name='IP 地址')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='客户端信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('last_seen_at', models.DateTimeField(auto_now=True, verbose_name='最近活跃时间')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否有效')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dashboard_login_sessions', to=settings.AUTH_USER_MODEL, verbose_name='管理员用户')),
            ],
            options={
                'verbose_name': '后台登录会话',
                'verbose_name_plural': '后台登录会话',
                'ordering': ['-last_seen_at', '-id'],
            },
        ),
        migrations.AddIndex(
            model_name='dashboardloginsession',
            index=models.Index(fields=['user', '-last_seen_at'], name='dash_sess_user_seen_idx'),
        ),
        migrations.AddIndex(
            model_name='dashboardloginsession',
            index=models.Index(fields=['key'], name='dash_sess_key_idx'),
        ),
    ]
