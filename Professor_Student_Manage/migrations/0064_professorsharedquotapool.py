from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Enrollment_Manage', '0001_initial'),
        ('Professor_Student_Manage', '0063_student_is_signate_giveup_table'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfessorSharedQuotaPool',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pool_name', models.CharField(max_length=100, verbose_name='共享名额池名称')),
                ('quota_scope', models.CharField(choices=[('master', '硕士共享池'), ('doctor', '博士共享池')], max_length=20, verbose_name='名额类型')),
                ('campus', models.CharField(choices=[('general', '不区分校区'), ('beijing', '北京'), ('yantai', '烟台')], default='general', max_length=20, verbose_name='适用校区')),
                ('total_quota', models.IntegerField(default=0, verbose_name='总名额')),
                ('used_quota', models.IntegerField(default=0, verbose_name='已用名额')),
                ('remaining_quota', models.IntegerField(default=0, verbose_name='剩余名额')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('notes', models.TextField(blank=True, default='', verbose_name='备注')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('professor', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='shared_quota_pools', to='Professor_Student_Manage.professor', verbose_name='导师')),
                ('subjects', models.ManyToManyField(related_name='shared_quota_pools', to='Enrollment_Manage.Subject', verbose_name='可使用专业')),
            ],
            options={
                'verbose_name': '导师共享名额池',
                'verbose_name_plural': '导师共享名额池',
            },
        ),
    ]
