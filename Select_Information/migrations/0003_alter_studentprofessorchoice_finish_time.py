# Generated by Django 3.2.8 on 2024-03-01 14:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Select_Information', '0002_remove_studentprofessorchoice_choice_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentprofessorchoice',
            name='finish_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='处理时间'),
        ),
    ]