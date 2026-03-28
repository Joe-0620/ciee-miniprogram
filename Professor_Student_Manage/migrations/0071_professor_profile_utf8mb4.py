from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0070_professor_heat_controls'),
    ]

    operations = [
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `Professor_Student_Manage_professor` "
                "CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `Professor_Student_Manage_professorprofilesection` "
                "CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
