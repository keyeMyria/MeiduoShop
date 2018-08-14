from django.shortcuts import render
from drf_haystack.viewsets import HaystackViewSet
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView

from goods.models import SKU
from goods.serializers import SKUSerializer, SKUIndexSerializer


# tips--商品列表
class SKUListView(ListAPIView):
    """
    sku列表数据
    """
    serializer_class = SKUSerializer

    filter_backends = (OrderingFilter,)
    """
    REST framework提供了对于排序的支持, 使用REST framework提供的OrderingFilter过滤器后端即可

    OrderingFilter过滤器要使用ordering_fields 属性来指明可以进行排序的字段有哪些
    """
    ordering_fields = ('create_time', 'price', 'sales')

    # note--查询的时候要根据不同的三级分类查询数据, 即需要动态的修改查询集
    # note--对于get_queryset函数内部拿到命名参数, 可以使用kwargs, 匿名参数可以使用args

    """
    DRF中：

    视图函数封装了几个属性：
    request.data            ==> 封装了所有post, put, patch等请求方法传递的所有参数, 以字典形式存储
    request.query_params    ==> 封装了所有的查询字符串参数
    self.kwargs             ==> 封装了所有的命名参数(即以路径形式传递的命名参数, request对象是无法直接获取的)
    self.args               ==> 封装了所有的匿名参数(即以路径形式传递的匿名参数, request对象是无法直接获取的)

    视图函数中如果调用了get_serializer方法获取序列化器对象的时候, 会为该序列化器对象添加三个属性
    self.context['request'] ==> 将视图中的request对象封装到了序列化器的context对象中
    self.context['view']    ==> 将视图本身作为对象封装到了序列化器的context对象中
    self.context['format']  ==> 将视图接收请求数据的格式format封装到了序列化器的context对象中

    """
    def get_queryset(self):
        # note--获取命名路径参数, 拿到分类
        category_id = self.kwargs['category_id']
        return SKU.objects.filter(category_id=category_id, is_launched=True)


# tips--商品搜索
class SKUSearchViewSet(HaystackViewSet):
    """
    SKU搜索
    """
    index_models = [SKU]

    serializer_class = SKUIndexSerializer




























