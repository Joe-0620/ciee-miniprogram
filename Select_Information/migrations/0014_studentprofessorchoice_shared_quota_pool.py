from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0064_professorsharedquotapool'),
        ('Select_Information', '0013_selectiontime_target'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofessorchoice',
            name='shared_quota_pool',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name='choices',
                to='Professor_Student_Manage.professorsharedquotapool',
                verbose_name='消耗的共享名额池',
            ),
        ),
    ]
