from django.conf.urls import url
from rest_framework import routers
from rest_framework_jwt.views import obtain_jwt_token

from . import views

urlpatterns = [
    url(r'^users/$', views.UserView.as_view()),
    url(r'^authorizations/$', obtain_jwt_token),
    url(r'^user/$', views.UserDetailView.as_view()),

    url(r'^email/$', views.EmailView.as_view()),  # 设置邮箱
    url(r'^emails/verification/$', views.VerifyEmailView.as_view()),  # 验证邮箱

    url(r'^browse_histories/$', views.UserBrowsingHistoryView.as_view())

]

router = routers.DefaultRouter()
router.register(r'addresses', views.AddressViewSet, base_name='addresses')

urlpatterns += router.urls
# POST /addresses/              新建  -> create
# PUT /addresses/<pk>/          修改  -> update
# GET /addresses/               查询  -> list
# DELETE /addresses/<pk>/       删除 -> destroy
# PUT /addresses/<pk>/status/   设置默认 -> status
# PUT /addresses/<pk>/title/    设置标题 -> title
