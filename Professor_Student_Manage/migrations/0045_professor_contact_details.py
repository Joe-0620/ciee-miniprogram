# Generated by Django 3.2.8 on 2024-03-26 06:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0044_professor_enroll_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='professor',
            name='contact_details',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='联系方式'),
        ),
    ]