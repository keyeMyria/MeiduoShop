from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.decorators import action

from rest_framework.generics import CreateAPIView, RetrieveAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework import mixins

from goods.models import SKU
from users import constants
from users import serializers
from users.models import User
from users.serializers import CreateUserSerializer, AddUserBrowsingHistorySerializer, SKUSerializer


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


# tips--地址管理
class AddressViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, GenericViewSet):
    """
    用户地址新增与修改, 添加, 删除
    """
    # tips--凡是要在一个视图函数中实现添加查询, 和删除修改一个具体对象, 都只能借助视图类来实现它
    # note--凡是使用视图集, 所有的方法都需要手动实现, 视图集只是帮我们完成了五个基本路由的路由器映射
    # note--视图集默认实现了五大方法的路由映射, 但是五大方法内部具体实现是空的需要手动创建! 继承扩展类只是为了不手动创建而已

    # NOTE--仔细体会本视图函数继承类的原因和重写的原因

    serializer_class = serializers.UserAddressSerializer
    permissions = [IsAuthenticated]

    # tips--对于修改对象, 需要注意的是查询集需要过滤, 只有当前用未被删除的地址才进行展示
    def get_queryset(self):
        return self.request.user.addresses.filter(is_deleted=False)

    # GET /addresses/
    def list(self, request, *args, **kwargs):
        """
        用户地址列表数据
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        user = self.request.user
        return Response({
            'user_id': user.id,
            'default_address_id': user.default_address_id,
            'limit': constants.USER_ADDRESS_COUNTS_LIMIT,
            'addresses': serializer.data,
        })

    # POST /addresses/ *********
    def create(self, request, *args, **kwargs):
        """
        保存用户地址数据
        """
        # note--这里本来已经继承了扩展类, 完全可以不用手写该方法, 但是为了进行判断, 使用了　继承+super+重写　等结合, 一箭双雕

        # 检查用户地址数据数目不能超过上限
        count = request.user.addresses.filter(is_deleted=False).count()
        if count >= constants.USER_ADDRESS_COUNTS_LIMIT:
            return Response({'message': '保存地址数据已达到上限'}, status=status.HTTP_400_BAD_REQUEST)

        # note--继承的目的就是为了使用super调用扩展类的super方法
        return super().create(request, *args, **kwargs)

    # delete /addresses/<pk>/
    def destroy(self, request, *args, **kwargs):
        """
        处理删除
        """
        address = self.get_object()

        # 进行逻辑删除
        address.is_deleted = True
        address.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    # put /addresses/pk/status/
    @action(methods=['put'], detail=True)
    def status(self, request, pk=None):
        """
        设置默认地址
        """
        address = self.get_object()
        request.user.default_address = address
        request.user.save()
        return Response({'message': 'OK'}, status=status.HTTP_200_OK)

    # put /addresses/pk/title/
    @action(methods=['put'], detail=True)
    def title(self, request, pk=None):
        """
        修改标题, 其实没必要使用序列化器
        """
        address = self.get_object()
        serializer = serializers.AddressTitleSerializer(instance=address, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# tips--历史记录
class UserBrowsingHistoryView(CreateAPIView):
    """
    用户浏览历史记录
    """
    permission_classes = [IsAuthenticated]
    serializer_class = AddUserBrowsingHistorySerializer

    # 使用一个视图函数要灵活, 虽然CreateAPIView只实现了post,　但是不代表我们不能写其他的
    # 这里我们能自定义get

    def get(self, request):
        """
        获取
        """
        user_id = request.user.id

        redis_conn = get_redis_connection("history")
        history = redis_conn.lrange("history_%s" % user_id, 0, constants.USER_BROWSING_HISTORY_COUNTS_LIMIT - 1)
        skus = []

        print(history)
        # note--为了保持查询出的顺序与用户的浏览历史保存顺序一致
        for sku_id in history:

            # 查询出的为字节类型
            sku = SKU.objects.get(id=sku_id)
            skus.append(sku)

        s = SKUSerializer(skus, many=True)
        return Response(s.data)

