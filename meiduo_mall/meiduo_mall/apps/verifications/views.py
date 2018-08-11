import random

from django.http import HttpResponse
from django.shortcuts import render
from django.views import View
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from meiduo_mall.libs.yuntongxun.sms import CCP
from meiduo_mall.utils.exceptions import logger
from users.models import User
from verifications.serializers import ImageCodeCheckSerializer
from . import constants
from meiduo_mall.libs.captcha.captcha import captcha
from celery_tasks.sms import sms_task


class ImageCodeView(View):
    """
    图片验证码
    """

    # 前端需要传送uuid, 后端根据uuid调用第三方工具生成图片和验证码
    # 将生成的图片返回给前端

    def get(self, request, image_code_id):
        """
        获取图片验证码
        """
        # 生成验证码图片
        text, image = captcha.generate_captcha()

        redis_conn = get_redis_connection("verify_codes")
        redis_conn.setex("img_%s" % image_code_id, constants.IMAGE_CODE_REDIS_EXPIRES, text)

        # 固定返回验证码图片数据，不需要REST framework框架的Response帮助我们决定返回响应数据的格式
        # 所以此处直接使用Django原生的HttpResponse即可
        return HttpResponse(image, content_type="images/jpg")


class SMSCodeView(GenericAPIView):
    """
    短信验证码
    """
    # 接受图片验证码,　uuid,　手机号
    # 校验, 由序列化器完成
    serializer_class = ImageCodeCheckSerializer

    # 生成短信验证码并异步发送
    def get(self, request, mobile):
        """
        创建短信验证码
        """
        # 判断图片验证码, 判断是否在60s内
        # note--get_serializer在创建序列化器对象的时候, 会传入三个属性(request, view, format)
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        # 生成短信验证码
        sms_code = "%06d" % random.randint(0, 999999)

        # 保存短信验证码  保存发送记录
        redis_conn = get_redis_connection('verify_codes')
        # redis_conn.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        # redis_conn.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # redis管道
        pl = redis_conn.pipeline()
        pl.setex("sms_%s" % mobile, constants.SMS_CODE_REDIS_EXPIRES, sms_code)
        pl.setex("send_flag_%s" % mobile, constants.SEND_SMS_CODE_INTERVAL, 1)

        # 让管道通知redis执行命令
        pl.execute()

        # 发送短信
        # try:
        #     ccp = CCP()
        #     expires = constants.SMS_CODE_REDIS_EXPIRES // 60    # 多少秒之后过期, 属于模板内容
        #     result = ccp.send_template_sms(mobile, [sms_code, expires], constants.SMS_CODE_TEMP_ID)
        # except Exception as e:
        #     logger.error("发送验证码短信[异常][ mobile: %s, message: %s ]" % (mobile, e))
        #     return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        # else:
        #     if result == 0:
        #         logger.info("发送验证码短信[正常][ mobile: %s ]" % mobile)
        #         return Response({'message': 'OK'})
        #     else:
        #         logger.warning("发送验证码短信[失败][ mobile: %s ]" % mobile)
        #         return Response({'message': 'failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 发送短信验证码
        # expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        # ccp = CCP()
        # ccp.send_template_sms(mobile, [sms_code, expires], constants.SMS_CODE_TEMP_ID)

        # 使用celery发送短信验证码
        expires = constants.SMS_CODE_REDIS_EXPIRES // 60
        sms_task.delay(mobile, sms_code, constants.SMS_CODE_TEMP_ID)

        return Response({"message": "OK"})


class UsernameCountView(APIView):
    """判断用户名是否存在"""
    """
    用户名数量
    """
    def get(self, request, username):
        """
        获取指定用户名数量
        """
        count = User.objects.filter(username=username).count()

        data = {
            'username': username,
            'count': count
        }

        return Response(data)


class MobileCountView(APIView):
    """
    手机号数量
    """
    def get(self, request, mobile):
        """
        获取指定手机号数量
        """
        count = User.objects.filter(mobile=mobile).count()

        data = {
            'mobile': mobile,
            'count': count
        }

        return Response(data)
