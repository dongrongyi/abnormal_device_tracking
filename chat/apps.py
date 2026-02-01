from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chat'

    def ready(self):
        # 延迟导入
        from django.db.models.signals import post_save
        from workflows.models import DeviceProcess
        from .signals import create_chatroom
        # 手动注册（替代装饰器，更灵活），post_save是django的内置信号
        post_save.connect(create_chatroom, sender=DeviceProcess,dispatch_uid='chat_create_chatroom') # connect()建立信号与接收者函数的绑定关系，dispatch_uid是（唯一标识），确保一个接收器只注册一次