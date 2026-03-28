from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0072_available_student_display_setting_and_student_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='accepted_weight',
            field=models.DecimalField(decimal_places=2, default=0.6, max_digits=5, verbose_name='已同意人数权重'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='calculation_scope',
            field=models.CharField(
                choices=[('overall', '按导师总量计算'), ('subject', '按当前学生专业计算')],
                default='overall',
                max_length=20,
                verbose_name='热度计算维度',
            ),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='high_threshold',
            field=models.DecimalField(decimal_places=2, default=3.0, max_digits=5, verbose_name='高热度阈值'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='medium_threshold',
            field=models.DecimalField(decimal_places=2, default=1.0, max_digits=5, verbose_name='中热度阈值'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='pending_weight',
            field=models.DecimalField(decimal_places=2, default=1.0, max_digits=5, verbose_name='待处理人数权重'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='rejected_weight',
            field=models.DecimalField(decimal_places=2, default=0.2, max_digits=5, verbose_name='已拒绝人数权重'),
        ),
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='very_high_threshold',
            field=models.DecimalField(decimal_places=2, default=6.0, max_digits=5, verbose_name='很高热度阈值'),
        ),
    ]
