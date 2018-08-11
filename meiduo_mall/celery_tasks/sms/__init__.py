from celery_tasks import app
from meiduo_mall.libs.yuntongxun.sms import CCP


# 创建celery任务
@app.task(name='sms_task')
def sms_task(mobile, sms_code, temp_id):
    ccp = CCP()
    ccp.send_template_sms(mobile, sms_code, temp_id)

    return "发送短信--任务执行完毕"

