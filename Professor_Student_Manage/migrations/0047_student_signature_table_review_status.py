# Generated by Django 3.2.8 on 2024-09-26 08:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0046_auto_20240924_0328'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='signature_table_review_status',
            field=models.BooleanField(default=False, verbose_name='导师意向表审核状态'),
        ),
    ]