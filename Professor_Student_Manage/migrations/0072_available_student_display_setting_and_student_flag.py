from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0071_professor_profile_utf8mb4'),
    ]

    operations = [
        migrations.CreateModel(
            name='AvailableStudentDisplaySetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=True, verbose_name='是否开放可选学生展示')),
                ('require_resume', models.BooleanField(default=False, verbose_name='仅展示已上传简历学生')),
                ('allowed_admission_years', models.JSONField(blank=True, default=list, verbose_name='允许展示届别')),
                ('allowed_batch_ids', models.JSONField(blank=True, default=list, verbose_name='允许展示批次')),
                ('allowed_postgraduate_types', models.JSONField(blank=True, default=list, verbose_name='允许展示培养类型')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '可选学生展示配置',
                'verbose_name_plural': '可选学生展示配置',
            },
        ),
        migrations.AddField(
            model_name='student',
            name='selection_display_enabled',
            field=models.BooleanField(default=True, verbose_name='允许显示在可选学生池'),
        ),
    ]
