from django.db import migrations, models


def update_professor_heat_thresholds(apps, schema_editor):
    ProfessorHeatDisplaySetting = apps.get_model('Professor_Student_Manage', 'ProfessorHeatDisplaySetting')
    setting, _ = ProfessorHeatDisplaySetting.objects.get_or_create(pk=1)
    setting.pending_weight = 1
    setting.accepted_weight = 0
    setting.rejected_weight = 0
    setting.medium_threshold = 2
    setting.high_threshold = 4
    setting.very_high_threshold = 6
    setting.save(
        update_fields=[
            'pending_weight',
            'accepted_weight',
            'rejected_weight',
            'medium_threshold',
            'high_threshold',
            'very_high_threshold',
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0074_professor_heat_target_year'),
    ]

    operations = [
        migrations.AlterField(
            model_name='professorheatdisplaysetting',
            name='accepted_weight',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='已同意人数权重'),
        ),
        migrations.AlterField(
            model_name='professorheatdisplaysetting',
            name='rejected_weight',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5, verbose_name='已拒绝人数权重'),
        ),
        migrations.AlterField(
            model_name='professorheatdisplaysetting',
            name='medium_threshold',
            field=models.DecimalField(decimal_places=2, default=2, max_digits=5, verbose_name='二级热度超出阈值'),
        ),
        migrations.AlterField(
            model_name='professorheatdisplaysetting',
            name='high_threshold',
            field=models.DecimalField(decimal_places=2, default=4, max_digits=5, verbose_name='三级热度超出阈值'),
        ),
        migrations.AlterField(
            model_name='professorheatdisplaysetting',
            name='very_high_threshold',
            field=models.DecimalField(decimal_places=2, default=6, max_digits=5, verbose_name='四级热度超出阈值'),
        ),
        migrations.RunPython(update_professor_heat_thresholds, migrations.RunPython.noop),
    ]
