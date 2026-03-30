from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0076_student_giveup_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='medium_ratio_threshold',
            field=models.DecimalField(decimal_places=2, default=1.5, max_digits=5, verbose_name='二级热度比例阈值'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='high_ratio_threshold',
            field=models.DecimalField(decimal_places=2, default=2.5, max_digits=5, verbose_name='三级热度比例阈值'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='very_high_ratio_threshold',
            field=models.DecimalField(decimal_places=2, default=4.0, max_digits=5, verbose_name='四级热度比例阈值'),
        ),
    ]
