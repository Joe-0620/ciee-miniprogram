from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0065_auto_20260326_1359'),
    ]

    operations = [
        migrations.AlterField(
            model_name='professor',
            name='proposed_quota_approved',
            field=models.BooleanField(default=False, verbose_name='寮€閫氳閫夋嫨璧勬牸'),
        ),
    ]
