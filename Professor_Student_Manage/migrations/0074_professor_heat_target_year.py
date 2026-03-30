from django.db import migrations, models


def set_professor_heat_defaults(apps, schema_editor):
    ProfessorHeatDisplaySetting = apps.get_model('Professor_Student_Manage', 'ProfessorHeatDisplaySetting')
    setting, _ = ProfessorHeatDisplaySetting.objects.get_or_create(pk=1)
    setting.calculation_scope = 'subject'
    setting.target_admission_year = 2026
    setting.save(update_fields=['calculation_scope', 'target_admission_year'])


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0073_professor_heat_setting_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='professorheatdisplaysetting',
            name='target_admission_year',
            field=models.PositiveIntegerField(default=2026, verbose_name='统计届别'),
        ),
        migrations.AlterField(
            model_name='professorheatdisplaysetting',
            name='calculation_scope',
            field=models.CharField(
                choices=[('overall', '按导师总量计算'), ('subject', '按当前学生专业计算')],
                default='subject',
                max_length=20,
                verbose_name='热度计算维度',
            ),
        ),
        migrations.RunPython(set_professor_heat_defaults, migrations.RunPython.noop),
    ]
