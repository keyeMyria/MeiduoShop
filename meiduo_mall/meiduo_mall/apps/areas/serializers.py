from rest_framework import serializers

from areas.models import Area


class AreaSerializer(serializers.ModelSerializer):
    """
    行政区划信息序列化器
    """
    class Meta:
        model = Area
        fields = ('id', 'name')


class SubAreaSerializer(serializers.ModelSerializer):
    """
    子行政区划信息序列化器
    """
    # note--注意这里无法使用外键关联, 所以手动指定比较方便
    subs = AreaSerializer(many=True, read_only=True)

    class Meta:
        model = Area
        fields = ('id', 'name', 'subs')
