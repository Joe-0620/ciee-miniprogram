# Generated by Django 3.2.8 on 2024-03-06 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0042_auto_20240306_0610'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='postgraduate_type',
            field=models.IntegerField(choices=[[1, '专业型(北京)'], [2, '学术型'], [3, '博士'], [4, '专业型(烟台)']], verbose_name='研究生类型'),
        ),
    ]