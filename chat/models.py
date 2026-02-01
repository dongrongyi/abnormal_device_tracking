# chat/models.py
# 聊天室Chatroom：id, member, content_object(process_id/bug_number), name(model_name_object_id), created_time,is_active,last_activity
# 消息Message：id, chatroom, owner, content, created_time
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Employee


class Chatroom(models.Model):
    members = models.ManyToManyField(Employee, related_name='chatrooms',blank=True)
    # GenericForeignKey的定义和使用
    # 为已存在的对象创建聊天室   ChatRoom.objects.create(content_object=existing_obj)   existing_obj是已存在的Process或Bug实例
    # 在对象创建时自动创建聊天室   在post_save信号中使用content_object = instance   instance是信号接收到的刚创建的Process或Bug实例
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE) # (表示是Process表还是Bug表)
    object_id = models.PositiveIntegerField() # (表示该表中的记录ID，如Process.id或Bug.id)
    content_object = GenericForeignKey('content_type', 'object_id') # 使用时只需要content_object=process/bug对象,  因为Django会自动设置content_type和object_id
    '''
        普通的ForeignKey只能让一个模型关联固定的某一个模型（比如Comment只能关联Article），
        而GenericForeignKey（简称 GFK）能让一个模型关联任意多个不同的模型（比如Comment既能关联Article，也能关联Video、Product）
        
        但仅用GenericForeignKey只能 “从评论找文章 / 视频”，无法 “从文章 / 视频找评论”，这时候就需要GenericRelation来实现反向查询
        
        GenericForeignKey 关联的 “多侧” 模型（如 Comment）	让当前模型能关联任意其他模型的任意实例，比如 Comment 关联 Article/Video
        GenericRelation	 被关联的 “一侧” 模型（如 Article/Video）	让被关联模型能快速查询关联的 GFK 模型实例（如 Article 查自己的所有 Comment）
        
        GenericForeignKey和GenericRelation是实现通用关联的配套搭档
        实际开发中，只要用了GenericForeignKey，就一定要在被关联模型上写GenericRelation，这是 Django 的最佳实践。
    '''
    name = models.CharField(max_length=255,
        unique=True,
        null=True, blank=True,
        help_text="聊天室唯一标识，如'process_123'或'bug_456'")  # 自动生成
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(
        default=True,
        help_text="聊天室是否活跃"
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        help_text="最后活动时间"
    )

    def save(self, *args, **kwargs):
        # 必须生成name（如果不存在）
        if not self.name and self.content_object:
            self.name = self._generate_name()
        super().save(*args, **kwargs)

    def _generate_name(self):
        """生成友好的显示名称"""
        obj = self.content_object
        print("self.content_type.model:",self.content_type.model)
        if self.content_type.model == 'deviceprocess': # ContentType模型有两个字段：app_label和model
            self.name = f"process_{obj.device.sn}" # process_sn
        elif self.content_type.model == 'bug':
            self.name = f"bug_{obj.bug_number}" # bug_bug号
        return self.name

    def __str__(self):
        return self.name or f"聊天室（未保存/{self.object_id}）"

    # 确保name不可修改（创建后）
    def clean(self):
        if self.pk:  # 已有实例
            original = Chatroom.objects.get(pk=self.pk)
            if original.name != self.name:
                raise ValidationError('name字段不可修改')

    @property
    def room_identifier(self):
        """WebSocket使用的标识符就是name"""
        return self.name


class Message(models.Model):
    chatroom = models.ForeignKey(Chatroom, on_delete=models.CASCADE)
    owner = models.ForeignKey(Employee, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.owner.username}:{self.content}"