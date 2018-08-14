
# 使用队列的位置
BROKER_URL = 'redis://127.0.0.1:6379/14'

# 任务结果存储位置
CELERY_RESULT_BACKEND = 'redis://127.0.0.1:6379/15'

# 设置时区
CELERY_TIMEZONE = 'Asia/Shanghai'

# 设置任务导入的模块
CELERY_IMPORTS = (
    'celery_tasks.sms',
    'celery_tasks.email',
    'celery_tasks.html',
)
