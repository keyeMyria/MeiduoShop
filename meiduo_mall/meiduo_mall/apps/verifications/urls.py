from django.conf.urls import url

from verifications.views import ImageCodeView, SMSCodeView, UsernameCountView, MobileCountView

urlpatterns = [
    url(r'^image_codes/(?P<image_code_id>[\w-]+)/', ImageCodeView.as_view()),
    url(r'^sms_codes/(?P<mobile>1[3-9]\d{9})/', SMSCodeView.as_view()),
    url(r'^usernames/(?P<username>\w{5,20})/count/$', UsernameCountView.as_view()),
    url(r'^mobiles/(?P<mobile>1[3-9]\d{9})/count/$', MobileCountView.as_view()),


]