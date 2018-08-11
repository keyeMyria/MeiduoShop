from django.shortcuts import render
from rest_framework import status

from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users import serializers
from users.models import User
from users.serializers import CreateUserSerializer


# tips--注册视图
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


# tips--详情视图
class UserDetailView(RetrieveAPIView):
    """
    用户详情
    """
    serializer_class = serializers.UserDetailSerializer
    permission_classes = [IsAuthenticated]

    # note--获取单个用户，且为登录用户，不需要查询数据库，直接使用request即可，所以需要重写get_object方法
    def get_object(self):
        return self.request.user


# tips--用户邮箱
class EmailView(UpdateAPIView):
    """
    保存用户邮箱
    """
    permission_classes = [IsAuthenticated]
    serializer_class = serializers.EmailSerializer

    def get_object(self, *args, **kwargs):
        return self.request.user


# tips--验证邮箱
class VerifyEmailView(APIView):
    """
    邮箱验证
    """
    def get(self, request):
        # note--获取token, DRF中所有的查询参数在query_params中, 所有路径参数在args(匿名), kwargs(命名)中

        token = request.query_params.get('token')
        if not token:
            return Response({'message': '缺少token'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证token, 该方法是静态方法, 所以不需要具体用户对象就可使用
        user = User.check_verify_email_token(token)
        if user is None:
            return Response({'message': '链接信息无效'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            user.email_active = True
            user.save()
            return Response({'message': 'OK'})
