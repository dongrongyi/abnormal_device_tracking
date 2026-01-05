from django.apps import AppConfig


class DiscussionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        # 手动注册（替代装饰器，更灵活）
        from django.db.models.signals import post_save
        from workflows.models import DeviceProcess
        from .signals import create_chatroom
        # connect()建立信号与接收者函数的绑定关系
        post_save.connect(create_chatroom, sender=DeviceProcess)