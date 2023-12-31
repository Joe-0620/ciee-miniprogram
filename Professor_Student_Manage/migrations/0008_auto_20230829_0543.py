# Generated by Django 3.2.8 on 2023-08-29 05:43

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0007_auto_20230827_1101'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='department',
            options={'verbose_name': '招生方向', 'verbose_name_plural': '招生方向'},
        ),
        migrations.AlterField(
            model_name='department',
            name='department_name',
            field=models.CharField(max_length=50, verbose_name='招生方向'),
        ),
        migrations.AlterField(
            model_name='professor',
            name='department',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='Professor_Student_Manage.department', verbose_name='所属招生方向'),
        ),
        migrations.AlterField(
            model_name='professor',
            name='department_position',
            field=models.IntegerField(choices=[[0, '非审核人'], [1, '方向审核人']], default=0),
        ),
    ]
