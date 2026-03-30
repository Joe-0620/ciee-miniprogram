from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0075_professor_heat_threshold_defaults'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='giveup_time',
            field=models.DateTimeField(blank=True, null=True, verbose_name='放弃时间'),
        ),
    ]
