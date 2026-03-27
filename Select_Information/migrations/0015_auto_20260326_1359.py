from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Select_Information', '0014_studentprofessorchoice_shared_quota_pool'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reviewrecord',
            name='file_id',
            field=models.CharField(max_length=500, verbose_name='文件 ID'),
        ),
        migrations.AlterField(
            model_name='studentprofessorchoice',
            name='status',
            field=models.IntegerField(
                choices=[(1, '已同意'), (2, '已拒绝'), (3, '请等待'), (4, '已取消'), (5, '已撤销')],
                default=3,
                verbose_name='状态',
            ),
        ),
    ]
