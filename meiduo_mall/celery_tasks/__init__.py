from celery import Celery

# 添加Django环境
import os
if not os.getenv('DJANGO_SETTINGS_MODULE'):
    os.environ['DJANGO_SETTINGS_MODULE'] = 'meiduo_mall.settings.dev'

# 创建celery应用
app = Celery('Meiduo')

# 加载celery配置
app.config_from_object('celery_tasks.config')
