import base64
import pickle

import redis

from django.shortcuts import render
from django_redis import get_redis_connection
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from carts import constants
from carts.serializers import CartSerializer, CartSKUSerializer, CartDeleteSerializer, CartSelectAllSerializer
from goods.models import SKU


# tips--购物车增删改查
class CartView(APIView):
    """
    购物车需要实现增删改查

    1. 购物车需要根据不同的登录状态保存到不同的位置
    　　登录用户保存在redis, 未登录用户保存在cookie

    2. 购物车需要保存sku_id, count, sku_selected
       cookie保存格式为:
       {
            sku_id: {
                "count": xxx,  // 数量
                "selected": True  // 是否勾选
            },
            sku_id: {
                "count": xxx,
                "selected": False
            },
        }

    　　redis保存格式为:
       user_id_sku: { sku_id: count, sku_id, count}
       user_id_selected: { sku_id, sku_id, sku_id}

    3. 因为全局设置了认证, DRF视图类在进行dispatch()分发前，会对请求进行身份认证、权限检查、流量控制, 始终都会执行
       只要请求携带了设置中设定的身份认证类要求的请求头, 就会进行验证
    　　如果不携带设置中设定的身份人在类要求的请求头, 就不会触发验证
       所以要认真考量携带与否...


    4. 为了判断用户是否登录, 需要前端始终传递jwt头部
       但所一旦使用了jwt, 请求头部包含了authorization就会被DRF验证器拦截验证, 但所如果未登录, 则会无法通过验证抛出错误


    """
    # note--因为这里请求头携带了jwt_token, 全局又配置了认证, 所以始终会触发jwt校验, 但是未登录用户的token是空的, jwt校验会报错
    # note--所以需要重写一个方法, perform_authentication
    # note--perform_authentication方法的最终目的就是通过request.user方法拿到当前的用户对象, 所以这里我们先不让其拿到任何用户对象

    def perform_authentication(self, request):
        # tips--先不获取用户对象, 由我们自己手动来获取
        # tips--该方法内部实际调用的所request.user方法来获取用户
        # tips--request.user获取用户的时候就会开启校验
        pass

    def post(self, request):
        # 先获取到sku_id, 校验是否存在
        # sku_id = request.query_params['sku_id']
        # count = request.query_params['count']
        # selected = request.query_params['selected']
        #
        # try:
        #     SKU.objects.get(id=sku_id)
        # except SKU.DoesNotExist:
        #     raise

        # note--注意反序列化必须使用命名参数
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sku_id = data['sku_id']
        count = data['count']
        selected = data['selected']

        # 判断用户是否登录
        # perform_authentication获取用户对象调用了request.user方法, 所以这里我们需要手动调用该方法
        # 尝试对请求的用户进行验证, 因为所个方法, 可能会抛出异常
        try:
            user = request.user
        except Exception:
            # 验证失败，用户未登录
            user = None
        if user is not None and user.is_authenticated:
            # 用户已登录，在redis中保存
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            # 记录购物车商品数量
            pl.hincrby('cart_%s' % user.id, sku_id, count)
            # 记录购物车的勾选项
            # 勾选
            if selected:
                pl.sadd('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            # 用户未登录保存在cookie
            cart = request.COOKIES.get('cart')
            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
            else:
                cart = {}

            sku = cart.get(sku_id)
            if sku:
                count += int(sku.get('count'))

            cart[sku_id] = {
                'count': count,
                'selected': selected
            }

            cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()

            response = Response(serializer.data, status=status.HTTP_201_CREATED)

            # 设置购物车的cookie
            # 需要设置有效期，否则是临时cookie
            response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)
            return response

    def get(self, request):
        # 判断用户是否登录
        try:
            user = request.user
        except Exception:
            # 验证失败，用户未登录
            user = None

        # 必须同时检查认证状态和是否存在
        if user is not None and user.is_authenticated:
            # 用户已登录，从redis中读取
            redis_conn = get_redis_connection('cart')
            redis_cart = redis_conn.hgetall('cart_%s' % user.id)
            redis_cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)
            cart = {}
            for sku_id, count in redis_cart.items():
                print(sku_id)
                print(count)
                cart[int(sku_id)] = {
                    'count': int(count),
                    'selected': sku_id in redis_cart_selected
                }
        else:
            # 用户未登录，从cookie中读取
            cart = request.COOKIES.get('cart')
            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
            else:
                cart = {}

        # 获取查询集并进行序列化
        skus = SKU.objects.filter(id__in=cart.keys())
        # 此时SKU不包含数量和勾选状态, 需要手动添加
        for sku in skus:
            sku.count = cart[sku.id]['count']
            sku.selected = cart[sku.id]['selected']

        serializer = CartSKUSerializer(skus, many=True)
        return Response(serializer.data)

    def put(self, request):
        # 修改购物车使用幂等性, 即后端只需要知道具体sku的具体状态即可
        # 提交的是最后的结果, 所以需要判断库存和商品是否存在
        serializer = CartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        sku_id = data['sku_id']
        count = data['count']
        selected = data['selected']

        # 尝试对请求的用户进行验证
        try:
            user = request.user
        except Exception:
            # 验证失败，用户未登录
            user = None

        if user is not None and user.is_authenticated:
            # 用户已登录，在redis中保存
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            pl.hset('cart_%s' % user.id, sku_id, count)
            if selected:
                pl.sadd('cart_selected_%s' % user.id, sku_id)
            else:
                pl.srem('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(serializer.data)
        else:
            # 用户未登录，在cookie中保存
            # 使用pickle序列化购物车数据，pickle操作的是bytes类型
            cart = request.COOKIES.get('cart')
            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
            else:
                cart = {}

            cart[sku_id] = {
                'count': count,
                'selected': selected
            }
            cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()

            response = Response(serializer.data)
            # 设置购物车的cookie
            # 需要设置有效期，否则是临时cookie
            response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)
            return response

    def delete(self, request):
        """
        删除购物车数据
        """
        serializer = CartDeleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sku_id = serializer.validated_data['sku_id']

        try:
            user = request.user
        except Exception:
            user = None

        if user is not None and user.is_authenticated:
            # 用户已登录，在redis中保存
            redis_conn = get_redis_connection('cart')
            pl = redis_conn.pipeline()
            pl.hdel('cart_%s' % user.id, sku_id)
            pl.srem('cart_selected_%s' % user.id, sku_id)
            pl.execute()
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            # 用户未登录，在cookie中保存
            response = Response(status=status.HTTP_204_NO_CONTENT)

            # 使用pickle序列化购物车数据，pickle操作的是bytes类型
            cart = request.COOKIES.get('cart')

            # 不存在则直接返回
            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
                if sku_id in cart:
                    del cart[sku_id]
                    cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()
                    # 设置购物车的cookie
                    # 需要设置有效期，否则是临时cookie
                    response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)
            return response


# tips--购物车全选与否
class CartSelectAllView(APIView):
    """
    购物车全选
    """
    def perform_authentication(self, request):
        """
        重写父类的用户验证方法，不在进入视图前就检查JWT
        """
        pass

    def put(self, request):
        serializer = CartSelectAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        selected = serializer.validated_data['selected']

        try:
            user = request.user
        except Exception:
            # 验证失败，用户未登录
            user = None

        if user is not None and user.is_authenticated:
            # 用户已登录，在redis中保存
            redis_conn = get_redis_connection('cart')
            cart = redis_conn.hgetall('cart_%s' % user.id)
            sku_id_list = cart.keys()

            # print(cart)
            # print(redis_conn.smembers('cart_selected_%s' % user.id))
            # note--b'num'转化成正常的数字
            # print(int(b'10'))

            if selected:
                # 全选
                redis_conn.sadd('cart_selected_%s' % user.id, *sku_id_list)
            else:
                # 取消全选
                redis_conn.srem('cart_selected_%s' % user.id, *sku_id_list)
            return Response({'message': 'OK'})
        else:
            # cookie
            cart = request.COOKIES.get('cart')

            response = Response({'message': 'OK'})

            if cart is not None:
                cart = pickle.loads(base64.b64decode(cart.encode()))
                for sku_id in cart:
                    cart[sku_id]['selected'] = selected
                cookie_cart = base64.b64encode(pickle.dumps(cart)).decode()
                # 设置购物车的cookie
                # 需要设置有效期，否则是临时cookie
                response.set_cookie('cart', cookie_cart, max_age=constants.CART_COOKIE_EXPIRES)

            return response


# tips--合并购物车, 不用其他接口：　pass
# tips--登录时候即合并, 传入必须的参数
# QQ登录(签发签名的时候合并), 正常登录(重写jwt自带的视图函数)
