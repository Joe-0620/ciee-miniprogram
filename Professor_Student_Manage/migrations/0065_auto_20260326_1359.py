from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0064_professorsharedquotapool'),
    ]

    operations = [
        migrations.AlterField(
            model_name='professor',
            name='proposed_quota_approved',
            field=models.BooleanField(default=False, verbose_name='开放被选择资格'),
        ),
        migrations.AlterField(
            model_name='professorsharedquotapool',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
