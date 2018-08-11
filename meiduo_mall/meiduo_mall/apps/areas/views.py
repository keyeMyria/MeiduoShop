from django.shortcuts import render


from rest_framework.viewsets import ReadOnlyModelViewSet

from areas.models import Area


# tips--省市区三级联动
from areas.serializers import AreaSerializer, SubAreaSerializer


class AreasViewSet(ReadOnlyModelViewSet):
    """
    行政区划信息

    １. 因为查询一个和查询多个使用一个视图实现, 所以使用查询集
    2. 因为所有数据都是在一张表, 所以查询省份的时候, 市区不应该出现, 所以需要重写查询集
    3. 因为一个省份的所有信息和查询所有省份无法使用同一个序列化器, 所以需要重写不同方法获取序列化器类的方法

    """
    # note--注意这里分页问题和最好的数据库查询缓存问题
    pagination_class = None  # 区划信息不分页

    def get_queryset(self):
        """
        提供数据集
        """
        if self.action == 'list':
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()

    # note--因为查询一个省份和一个省份的所有市区无法使用同一个序列化器, 所以这里需要重写
    # note--注意, 重写的是获取序列化器类的方法, 而不是获取序列化器实例对象的方法!
    def get_serializer_class(self):
        """
        提供序列化器
        """
        if self.action == 'list':
            return AreaSerializer
        else:
            return SubAreaSerializer
