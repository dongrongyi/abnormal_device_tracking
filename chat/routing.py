from django.urls import re_path

from chat.consumers import ChatConsumer

'''
    routing.py（Channels 的路由文件）和 Django 的urls.py逻辑高度相似，核心都是 “路径匹配 → 绑定处理逻辑”，核心区别是：
        urls.py：匹配HTTP/HTTPS 请求，绑定 Django 的视图函数 / 类；
        routing.py：匹配WebSocket/ASGI 请求，绑定 Channels 的 Consumer（消费者）
'''

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<name>\w+)/$", ChatConsumer.as_asgi()), # as_asgi将 Consumer 类转换为符合 ASGI 规范的应用实例
]