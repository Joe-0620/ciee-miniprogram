# Generated by Django 3.2.8 on 2023-09-25 16:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0021_auto_20230925_1626'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='department',
            name='remained_academic_quota',
        ),
        migrations.RemoveField(
            model_name='department',
            name='remained_doctor_quota',
        ),
        migrations.RemoveField(
            model_name='department',
            name='remained_professional_quota',
        ),
        migrations.AddField(
            model_name='department',
            name='used_academic_quota',
            field=models.IntegerField(default=0, verbose_name='学硕已用指标'),
        ),
        migrations.AddField(
            model_name='department',
            name='used_doctor_quota',
            field=models.IntegerField(default=0, verbose_name='博士已用指标'),
        ),
        migrations.AddField(
            model_name='department',
            name='used_professional_quota',
            field=models.IntegerField(default=0, verbose_name='专硕已用指标'),
        ),
    ]