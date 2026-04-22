from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0077_professor_heat_ratio_thresholds'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlternatePromotionSetting',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_promote_on_giveup', models.BooleanField(default=True, verbose_name='放弃录取后自动递补候补学生')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '候补递补配置',
                'verbose_name_plural': '候补递补配置',
            },
        ),
    ]
