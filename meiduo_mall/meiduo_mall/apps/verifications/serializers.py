from django_redis import get_redis_connection
from rest_framework import serializers


class ImageCodeCheckSerializer(serializers.Serializer):
    image_code_id = serializers.UUIDField()
    text = serializers.CharField(max_length=4, min_length=4)

    # 手机号这里也可以校验
    def validate(self, attrs):
        image_code_id = attrs['image_code_id']
        text = attrs['text']

        # 查询真实图片验证码
        redis_conn = get_redis_connection('verify_codes')
        real_image_code_text = redis_conn.get('img_%s' % image_code_id)
        if not real_image_code_text:
            raise serializers.ValidationError('图片验证码无效')

        # 删除图片验证码
        redis_conn.delete('img_%s' % image_code_id)

        # 比较图片验证码
        real_image_code_text = real_image_code_text.decode()
        if real_image_code_text.lower() != text.lower():
            raise serializers.ValidationError('图片验证码错误')

        # 判断是否在60s内
        # get_serializer在创建序列化器对象的时候, 会传入三个属性(request,view,format)
        # django的类视图对象中, kwargs属性保存了路径提取出来的参数
        # note--之所以不能使用request获取手机号,　是因为手机号是命名参数, 无法传入request的

        mobile = self.context['view'].kwargs['mobile']
        send_flag = redis_conn.get("send_flag_%s" % mobile)
        if send_flag:
            raise serializers.ValidationError('请求次数过于频繁')

        return attrs