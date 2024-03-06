from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Student
from .models import Professor
from django.db import models

@receiver(post_save, sender=Student)
def create_student_user(sender, instance, created, **kwargs):
    if created and not instance.user_name:
        user = User(username=instance.candidate_number)
        password = instance.candidate_number
        # password = instance.identify_number
        user.set_password(password)
        # user.set_unusable_password()  # 不设置密码
        user.save()
        instance.user_name = user
        instance.save()

@receiver(post_save, sender=Professor)
def create_professors_user(sender, instance, created, **kwargs):
    if created and not instance.user_name:
        # print("导师信号触发，且导师刚创建")
        user = User(username=instance.teacher_identity_id)
        password = instance.teacher_identity_id
        user.set_password(password)
        # user_name.set_unusable_password()  # 不设置密码
        user.save()
        instance.user_name = user
        instance.save()