from chat.models import Chatroom


def create_chatroom(sender,instance,created,**kwargs):
    if created:
        try:
            result = Chatroom.objects.create(content_object=instance)
            print("Chatroom创建结果:", result)  # 新增这行
        except Exception as e:
            print("创建失败：", e)
