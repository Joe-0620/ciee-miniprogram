from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Professor_Student_Manage', '0067_admissionbatch_student_login_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProfessorProfileSection',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=50, verbose_name='模块标题')),
                ('content', models.TextField(verbose_name='模块内容')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序值')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('professor', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='profile_sections', to='Professor_Student_Manage.professor', verbose_name='导师')),
            ],
            options={
                'verbose_name': '导师主页自定义模块',
                'verbose_name_plural': '导师主页自定义模块',
                'ordering': ['sort_order', 'id'],
            },
        ),
    ]
