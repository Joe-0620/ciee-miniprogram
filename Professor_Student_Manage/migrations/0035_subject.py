# Generated by Django 3.2.8 on 2024-03-05 14:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0034_alter_wechataccount_session_key'),
    ]

    operations = [
        migrations.CreateModel(
            name='Subject',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('subject_name', models.CharField(max_length=50, verbose_name='专业名称')),
                ('subject_code', models.CharField(max_length=10, verbose_name='专业代码')),
                ('subject_type', models.IntegerField(choices=[[0, '专硕'], [1, '学硕'], [2, '博士']], max_length=10, verbose_name='专业所属类别')),
                ('subject_department', models.ManyToManyField(null=True, related_name='subjects', to='Professor_Student_Manage.Department', verbose_name='可选该专业的方向')),
            ],
            options={
                'verbose_name': '专业',
                'verbose_name_plural': '专业',
            },
        ),
    ]