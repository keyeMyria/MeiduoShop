import redis
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django_redis import get_redis_connection
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from goods.models import SKU
from meiduo_mall.utils.exceptions import logger
from orders.models import OrderInfo, OrderGoods


class CartSKUSerializer(serializers.ModelSerializer):
    """
    购物车商品数据序列化器
    """
    count = serializers.IntegerField(label='数量')

    class Meta:
        model = SKU
        fields = ('id', 'name', 'default_image_url', 'price', 'count')


class OrderSettlementSerializer(serializers.Serializer):
    """
    订单结算数据序列化器

    多个字段的序列化过程
    """
    freight = serializers.DecimalField(label='运费', max_digits=10, decimal_places=2)
    skus = CartSKUSerializer(many=True)


class SaveOrderSerializer(serializers.ModelSerializer):
    """
    下单数据序列化器
    """
    class Meta:
        model = OrderInfo
        fields = ('order_id', 'address', 'pay_method')
        read_only_fields = ('order_id',)

        # 需要校验的字段:
        extra_kwargs = {
            'address': {
                'write_only': True,
                'required': True,
            },
            'pay_method': {
                'write_only': True,
                'required': True
            }
        }

    # note--涉及到对多个数据库的操作, 需要开启事务!
    def create(self, validated_data):
        """
        保存订单
        """
        # 获取当前下单用户
        # note--注意context是python标准字典, 但是request对象不是, 所以使用request.user
        user = self.context['request'].user

        # 获取地址支付信息
        pay_method = validated_data['pay_method']
        address = validated_data['address']

        # 组织订单编号 20170903153611+user.id
        # timezone.now() -> datetime
        order_id = timezone.now().strftime('%Y%m%d%H%M%S') + ('%09d' % user.id)


        """
        Django提供了数据库操作的事务机制, 使用方法：

        1. @transaction.atomic　装饰一个函数, 则函数里面所有的数据库操作都默认开启了事务机制

        2. with transaction.atomic(): 使用with语句, 则只有with内部的数据库操作才开启了事物

        保存点：事务支持记录保存点, 可以根据需要手动回到保存点:

        1. 创建保存点
        save_id = transaction.savepoint()

        2. 回滚到保存点
        transaction.savepoint_rollback(save_id)

        3. 提交从保存点到当前状态的所有数据库事务操作
        transaction.savepoint_commit(save_id)
        """
        # 生成订单(如果事务未完成则也不删除redis)
        with transaction.atomic():
            # note--创建一个保存点()
            save_id = transaction.savepoint()

            try:
                order = OrderInfo.objects.create(
                    order_id=order_id,
                    user=user,
                    address=address,
                    total_count=0,
                    total_amount=Decimal(0),
                    freight=Decimal(10),
                    pay_method=pay_method,
                    status=OrderInfo.ORDER_STATUS_ENUM['UNSEND'] if pay_method == OrderInfo.PAY_METHODS_ENUM['CASH'] else OrderInfo.ORDER_STATUS_ENUM['UNPAID']
                )

                # 获取购物车信息
                redis_conn = get_redis_connection("cart")   # type: redis.StrictRedis
                redis_cart = redis_conn.hgetall("cart_%s" % user.id)
                cart_selected = redis_conn.smembers('cart_selected_%s' % user.id)

                # tips--构建勾选商品数据结构
                # 查询所有的商品, 构建　{ sku_id: count } 数据格式
                # cart = {}
                # for sku_id, count in redis_cart.items():
                #     cart[int(sku_id)] = int(redis_cart[sku_id])

                # 查询所有的勾选产品的状态
                # selected = []
                # for i in cart_selected:
                #     selected.append(int(i))

                # note-- 构建勾选商品数据结构:这种方法更高效
                # 构建一个　{ select_sku_id: count }　数据格式, 将bytes类型转换为int类型
                cart = {}
                for sku_id in cart_selected:
                    cart[int(sku_id)] = int(redis_cart[sku_id])

                # 查询出所有购买的商品数据
                # skus = SKU.objects.filter(id__in=cart.keys())

                # 处理订单商品
                sku_id_list = cart.keys()
                # for sku in skus:
                for sku_id in sku_id_list:
                    while True:
                        sku_count = cart[sku_id]
                        sku = SKU.objects.get(id=sku_id)

                        # 判断库存
                        origin_stock = sku.stock  # 原始库存
                        origin_sales = sku.sales  # 原始销量

                        if sku_count > origin_stock:
                            transaction.savepoint_rollback(save_id)
                            raise serializers.ValidationError('商品库存不足')

                        # 用于演示并发下单
                        # import time
                        # time.sleep(5)

                        # 减少库存, 然后再更新
                        new_stock = origin_stock - sku_count
                        new_sales = origin_sales + sku_count

                        # sku.stock = new_stock
                        # sku.sales = new_sales

                        # note--在一句内完成数据的更新, 避免出现数据的变动

                        # tips--根据原始库存条件更新, 返回更新的条目数, 乐观锁
                        # tips--返回受影响的行数(如果更新时候的stock是原始的stock才会进行更新, 否则循环执行)
                        # 更新的时候判断此时的库存是否是之前查询出的库存
                        ret = SKU.objects.filter(id=sku.id, stock=origin_stock).update(stock=new_stock, sales=new_sales)
                        if ret == 0:
                            continue

                        # 只有乐观锁更新成功才继续执行
                        sku.save()

                        # 累计商品的SPU 销量信息, 这里不需要使用乐观锁进行锁定
                        sku.goods.sales += sku_count
                        sku.goods.save()

                        # 累计订单基本信息的数据, 每循环一个产品则累加一次
                        order.total_count += sku_count                  # 累计商品数
                        order.total_amount += (sku.price * sku_count)   # 累计总金额

                        # 保存订单商品
                        OrderGoods.objects.create(
                            order=order,
                            sku=sku,
                            count=sku_count,
                            price=sku.price,
                        )

                        # 更新成功
                        break

                    # 更新订单的金额数量信息
                    order.total_amount += order.freight
                    order.save()

            except ValidationError:
                # tips--对于库存不足的错误, 直接往外抛出
                # tips--因为上面已经回滚过一次了, 下面的exception会进行二次回滚, 没有必要
                # tips--所以对于上面已经导致回滚过一次的异常, 我们直接抛出, 不再回滚
                raise
            except Exception as e:
                # note--try_except语句可以抛出多个错误!
                logger.error(e)
                # note--回滚到保存点的数据库状态, 这里只是作为演示使用, 现实需要灵活使用
                # note--这里主要捕获其他非库存导致的数据库异常触发回滚
                transaction.savepoint_rollback(save_id)

                # 且错误不会被处理, 直接抛出,　因为下面的操作也不能继续了
                raise

            # 提交事务
            transaction.savepoint_commit(save_id)

            # 更新redis中购物车的数据
            pl = redis_conn.pipeline()
            pl.hdel('cart_%s' % user.id, *cart_selected)
            pl.srem('cart_selected_%s' % user.id, *cart_selected)
            pl.execute()

            """
            MySQL数据库事务隔离级别主要有四种：

            Serializable 串行化，一个事务一个事务的执行
            Repeatable read 可重复读，无论其他事务是否修改并提交了数据，在这个事务中看到的数据值始终不受其他事务影响
            Read committed 读取已提交，其他事务提交了对数据的修改后，本事务就能读取到修改后的数据值
            Read uncommitted 读取为提交，其他事务只要修改了数据，即使未提交，本事务也能看到修改后的数据值

            默认为Repeatable read, 如果要使用乐观锁, 需要改为读取已提交, 即其他事物修改之后本事务里面能看到

            """
            return order



