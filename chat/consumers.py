import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from chat.models import Message, Chatroom


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        @sync_to_async
        def get_chatroom():
            return Chatroom.objects.get(name=self.name)

        self.name = self.scope["url_route"]["kwargs"]["name"]
        self.room_group_name = f"chat_{self.name}"
        self.owner = self.scope["user"] # 通过Channels的AuthMiddleware从WebSocket握手时的cookie/session中提取的
        self.chatroom = await get_chatroom()

        print(f"WebSocket连接请求: 路径参数room ='{self.name}', 群组名 ='{self.room_group_name}'")
        # 将通道名加入 Redis 对应组的列表中，需要注意的是：Daphne 的 “通道名→连接实例” 映射 是在框架内部更早阶段（调用connect之前，daphne服务器对WebSocket 请求握手验证时）自动完成的
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)  # channel_name是这个连接在通道层中的唯一ID

        @sync_to_async
        def save_chatroom_member(owner, chatroom_id): # 把当前用户加入到聊天室
            chatroom = Chatroom.objects.filter(id=chatroom_id).first()
            if owner not in chatroom.members.all():
                chatroom.members.add(owner)
                chatroom.save()
        await save_chatroom_member(self.owner, self.chatroom.id)

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # 接收服务器消息
    async def receive(self, text_data):
        # 消息是否抵达Consumer
        print(f"Consumer.receive 收到原始数据: {text_data}")
        text_data_json = json.loads(text_data)
        message_content = text_data_json["message_content"]
        chatroom_id = text_data_json["chatroom_id"]

        # 消息解析和准备发送的群组
        print(f"Consumer.receive 解析消息: '{message_content}', 目标群组: '{self.room_group_name}', 连接名: '{self.channel_name}'")

        # 定义异步函数save_chat_message 保存消息到数据库
        @sync_to_async  # sync_to_async装饰器：异步customer调用同步代码（如 Django ORM、同步业务函数）时使用
        def save_chat_message(message_content, owner,chatroom_id):
            return Message.objects.create(content=message_content, owner=owner, chatroom_id=chatroom_id)


        # 保存消息（await 调用）
        self.message = await save_chat_message(message_content,self.owner,chatroom_id)

        self.message_data = {
            "content": self.message.content,
            "owner": self.message.owner.username,
            "created_at": self.message.created_at.strftime("%Y-%m-%d %H:%M:%S"),

        }

        # 发送消息到群组，让聊天室的每一个成员都能实时收到消息
        await self.channel_layer.group_send( # 该方法实际做的事情是 channel-redis从Redis查询组内所有channel，对每个channel: LPUSH + PUBLISH，把消息推送到对应通道的消息队列中，并通知所有daphne实例来消息了
            # 在Django Channels中，当 group_send 发送的事件中的 type 字段被框架接收后，它会在调用消费者实例的方法前，**自动将类型字符串中的点 . 替换为下划线 _**
            self.room_group_name, {"type": "chat.message", "message": self.message_data}
        )
        print(f"Consumer.receive group_send调用完成")
        # await self.send(text_data=json.dumps({"message": message}))


    # 当daphne实例监听到消息时，确认是否是自己处理的通道，如果是，从redis消息队列中取出消息，触发该函数将消息“发送”到用户浏览器
    async def chat_message(self, event): # 组发送时间的处理函数
        print(f"Consumer.chat_message 收到广播事件: {event}")
        message = event["message"]
        # 实质上这里的消费者的send方法只是给daphne服务器发送了格式化后的数据和send command，实际发送消息的任务是由daphne服务器完成的
        await self.send(text_data=json.dumps({"message": message}))
        print(f"Consumer.chat_message WebSocket发送: '{message}'")