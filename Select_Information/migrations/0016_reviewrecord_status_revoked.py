from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Select_Information', '0015_auto_20260326_1359'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reviewrecord',
            name='status',
            field=models.IntegerField(
                choices=[(1, '已通过'), (2, '已驳回'), (3, '待审核'), (4, '已撤销')],
                default=3,
                verbose_name='状态',
            ),
        ),
    ]
