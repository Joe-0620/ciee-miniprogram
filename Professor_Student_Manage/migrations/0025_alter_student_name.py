# Generated by Django 3.2.8 on 2024-03-01 14:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0024_auto_20240227_0601'),
    ]

    operations = [
        migrations.AlterField(
            model_name='student',
            name='name',
            field=models.CharField(max_length=100, verbose_name='学生姓名'),
        ),
    ]
