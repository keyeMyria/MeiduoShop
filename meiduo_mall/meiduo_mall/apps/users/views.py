from django.shortcuts import render

from rest_framework.generics import CreateAPIView

from users.serializers import CreateUserSerializer


class UserView(CreateAPIView):
    """
    url(r'^users/$', views.UserView.as_view()),
    用户注册
    传入参数：
        username, password, password2, sms_code, mobile, allow
    """
    # 校验, 所有字段全部都需要校验, 部分字段不需要序列化输出
    # 创建
    # 返回

    serializer_class = CreateUserSerializer
