from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from Professor_Quota_Review.models import AdmissionQuotaApproval
from django.db import models
from Professor_Student_Manage.signals import create_professors_user
from Professor_Student_Manage.models import Professor

@receiver(pre_delete, sender=AdmissionQuotaApproval)
def reset_professor_quota(sender, instance, **kwargs):
    try:
        professor = instance.professor

        if professor:
            
            # 解除保存之前的信号绑定
            post_save.disconnect(create_professors_user, sender=Professor)

            # 重置导师的相关字段
            professor.proposed_quota_approved = False
            professor.academic_quota = 0
            professor.professional_quota = 0
            professor.professional_yt_quota = 0
            professor.doctor_quota = 0
            professor.save()

            # 重新绑定信号
            post_save.connect(create_professors_user, sender=Professor)
    except Exception as e:
        # 处理任何可能的异常
        pass
