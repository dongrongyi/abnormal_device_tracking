from chat.models import Chatroom
import logging
from django.db import IntegrityError


# 配置日志（替代print，日志会写入Gunicorn日志）
logger = logging.getLogger(__name__)
# 定义接收器函数
def create_chatroom(sender,instance,created,**kwargs):
    if created:
        try:
            # 第一步：先检查是否已存在关联的Chatroom，避免重复创建
            # 假设Chatroom的content_object是通用外键，用content_type和object_id过滤
            from django.contrib.contenttypes.models import ContentType
            ct = ContentType.objects.get_for_model(instance)
            chatroom_exists = Chatroom.objects.filter(
                content_type=ct,
                object_id=instance.pk
            ).exists()

            if chatroom_exists:
                logger.warning(f"Chatroom已存在：{ct.model} - {instance.pk}")
                return  # 已存在则跳过，避免重复创建

            # 第二步：创建Chatroom（若name自动生成，确保生成逻辑唯一）
            result = Chatroom.objects.create(content_object=instance)
            logger.info(f"Chatroom创建成功：{result.id}，关联实例：{instance}")

            # 精准捕获唯一约束冲突异常
        except IntegrityError as e:
            logger.error(f"Chatroom创建失败（唯一约束冲突）：{e}，关联实例：{instance}")


            # 捕获其他异常
        except Exception as e:
            logger.error(f"Chatroom创建失败（未知错误）：{e}，关联实例：{instance}", exc_info=True)
