# MeiduoShop
美多商城

我们这个项目是B2C电子商务网站
采用了Django作为主体框架, 结合DRF框架设计了restful风格的API接口实现了前后端的分离.
我们的项目分为前台和后台, 前台提供了广告的展示, 商品的展示,　商品的搜索,　商品的详情, 用户登录注册, 第三方登录, 地址管理,　历史记录
购物车模块, 订单模块, 支付模块等, 后台直接使用了Django提供的后台,就主要是商品数据的管理　

首页上部分是广告的轮播图, 轮播图左侧是商品分类的选项卡, 上部搜索框和网站的logo
首页下部分是根据不同楼层展示的不同分离的广告, 通过选项卡或搜索可以进入商品分类的列表页
通过产品可以进入详情页, 包含商品的规格图片,　商品介绍, 评论等

我主要参与的模块是用户模块
比如登录注册使用到了云通讯, 第三方扩展
对于这部分的数据存储使用的redis, 然后使用了redis管道技术减少了与redis通信的消耗
对于手机号和用户名我们会通过数据库查询检查是否重名

我们还实现了第三方的ＱＱ登录, 通过建立一张ＱＱ用户的openid和用户的外键关联的表判断是否三第一次使用登录到我们的网站
这个过程中还使用了istdnag来进行openid的签名保证数据的可靠性

然后就是登录之后我们会使用jwt进行手动签名，这里要注意改写jwt的签名方法, 因为默认三没有用户payload部分的内容

登录的时候使用的是jwt通过的默认视图, 这里需要注意后期我们处理购物车的时候要重写该视图的提供的认证方法
因为默认三开启了jwta authneciti, 所以在购物车的时候会判断用户是否登录将数据存储到不同的位
所以要求前端必须带上authorizaton头部, 但是由于匿名用户的token是空的回导致认证失败, 这个人在的过程是
在进入视图函数就立马出发的, 会通过perform_authentication来调用request,userr 所以这里我们需要重写为pass改懒加载
在我没需要判断的时候手动出发reuqet,user去认证用户

在处理短信验证的时候使用了cors策略来完成跨域请求的处理

邮箱注册是哟改了djago提供的email模块完成邮箱的发送, 使用了istdanger来进行邮箱用户名和地址的签名生成链接然后认证

然后就用户地址这部分使用的了数据库的子关联三级查询，所使用到了drf-kuozhan, 使用其通过的扩展类， 来完成数据库的缓
用户地址管理就主要三数据哭的增删茶


在说一下购物车模块
主要是要实现根据用户状态保存数据到不同的位置
登录用户redis. 未登录使用cookie
最终要完成购物车的合并, 这部分主要是是使用了redis的管道操作, cookie操作

在说一下订单模块
在用户下单的时候会使用到了涉及到了多个数据哭的操作，　所有使用了djnago提供的transaction,.aotick开启了事物
然后在下单的时候为了解决并发导致库存不足的时候用户下单成功问题，　考虑使用了数据哭的乐观锁技术
同要配合修该mysqld 事物格力机制


商品详参与比较少就没了静态化, fastdfs, dockerdneg

