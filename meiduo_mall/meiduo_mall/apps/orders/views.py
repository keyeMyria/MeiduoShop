import redis
from decimal import Decimal
from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated


from goods.models import SKU
from orders.serializers import OrderSettlementSerializer, SaveOrderSerializer


# tips--订单结算页面
class OrderSettlementView(APIView):
    """
    订单结算页面所需的数据从购物车中勾选而来
    请求方式: GET /orders/settlement/
    请求参数: 无
    返回数据: JSON

    """
    # 结算必须登录
    # 数据展示来自redis的基本数据和商品详情数据
    # 额外添加运费字段
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """
        获取
        """
        user = request.user

        # data = {}
        # 查询redis数据
        # redis_conn = get_redis_connection('cart')   # type: redis.StrictRedis
        # select_list = redis_conn.smembers('cart_selected_%s' % user.id)
        # sku_count_list = redis_conn.hgetall('cart_%s' % user.id)
        # 只展示勾选状态的商品

        # sku_list = []
        #
        # for select_id in select_list:
        #     count = sku_count_list[select_id]
        #     sku = SKU.objects.get(id=int(select_id))
        #     sku.count = count
        #     sku_list.append(sku)

        # 从购物车中获取用户勾选要结算的商品信息
        redis_conn = get_redis_connection('cart')
        redis_cart = redis_conn.hgetall('cart_%s' % user.id)
        cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)

        cart = {}

        # tips--构造一个　{ sku_id: count } 的数据格式
        for sku_id in cart_selected:
            cart[int(sku_id)] = int(redis_cart[sku_id])

        # 查询商品信息, 并添加额外的字段
        # note--python中字典和类的实例对象是不一样的!
        # note--类的实例对象是可以通过点操作熟悉的, 也是可变类型
        skus = SKU.objects.filter(id__in=cart.keys())
        for sku in skus:
            sku.count = cart[sku.id]

        # 运费, Decimal运算速度慢, 但是精度高
        freight = Decimal('10.00')

        # 直接只序列化商品也可以
        # 构造一个对象即可, 单独序列化skus
        serializer = OrderSettlementSerializer({'freight': freight, 'skus': skus})
        return Response(serializer.data)


# tips--保存订单页面
class SaveOrderView(CreateAPIView):
    """
    保存订单
    """
    permission_classes = [IsAuthenticated]
    serializer_class = SaveOrderSerializer

