# Generated by Django 3.2.8 on 2024-03-05 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0033_auto_20240305_1350'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wechataccount',
            name='session_key',
            field=models.CharField(max_length=255),
        ),
    ]
