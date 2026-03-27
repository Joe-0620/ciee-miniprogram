from django.db import migrations, models
from django.utils import timezone


def seed_selection_time_targets(apps, schema_editor):
    SelectionTime = apps.get_model('Select_Information', 'SelectionTime')
    rows = list(SelectionTime.objects.order_by('id'))
    now = timezone.now()

    student_row = rows[0] if rows else None
    professor_row = rows[1] if len(rows) > 1 else None

    if student_row:
        student_row.target = 'student'
        student_row.save(update_fields=['target'])
    else:
        student_row = SelectionTime.objects.create(
            target='student',
            open_time=now,
            close_time=now,
        )

    if professor_row:
        professor_row.target = 'professor'
        professor_row.save(update_fields=['target'])
    else:
        SelectionTime.objects.create(
            target='professor',
            open_time=student_row.open_time,
            close_time=student_row.close_time,
        )

    for extra_row in rows[2:]:
        extra_row.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('Select_Information', '0012_reviewrecord_review_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='selectiontime',
            name='target',
            field=models.CharField(
                choices=[('student', '学生'), ('professor', '导师')],
                default='student',
                max_length=20,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(seed_selection_time_targets, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='selectiontime',
            name='target',
            field=models.CharField(
                choices=[('student', '学生'), ('professor', '导师')],
                default='student',
                max_length=20,
                unique=True,
            ),
        ),
    ]
