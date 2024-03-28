# import os
# from celery import Celery

# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wxcloudrun.settings')

# app = Celery('wxcloudrun')
# app.config_from_object('django.conf:settings', namespace='CELERY')

# # 自动从所有已注册的Django app中加载任务
# app.autodiscover_tasks()