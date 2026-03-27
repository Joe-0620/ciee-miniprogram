from django.db import migrations, models
import django.db.models.deletion

import Professor_Student_Manage.models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0066_alter_professor_proposed_quota_approved'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdmissionBatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='批次名称')),
                ('admission_year', models.PositiveIntegerField(default=Professor_Student_Manage.models.get_default_admission_year, verbose_name='届别')),
                ('batch_code', models.CharField(blank=True, default='', max_length=50, verbose_name='批次编码')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序值')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('description', models.TextField(blank=True, default='', verbose_name='批次说明')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '招生批次',
                'verbose_name_plural': '招生批次',
                'ordering': ['-admission_year', 'sort_order', 'id'],
                'unique_together': {('admission_year', 'name')},
            },
        ),
        migrations.AddField(
            model_name='student',
            name='admission_batch',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='students', to='Professor_Student_Manage.admissionbatch', verbose_name='招生批次'),
        ),
        migrations.AddField(
            model_name='student',
            name='admission_year',
            field=models.PositiveIntegerField(default=2025, verbose_name='届别'),
        ),
        migrations.AddField(
            model_name='student',
            name='can_login',
            field=models.BooleanField(default=True, verbose_name='允许登录小程序'),
        ),
    ]
