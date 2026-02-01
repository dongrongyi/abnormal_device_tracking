from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.utils import timezone
from accounts.models import Employee


# Create your models here.
class Bug(models.Model):
    bug_number = models.CharField(unique=True,max_length=15)
    title = models.CharField(max_length=100, verbose_name="bug标题",null=True,blank=True)
    description = models.CharField(max_length=500, verbose_name="bug描述",null=True,blank=True)
    status = models.CharField(max_length=20, choices=[("processing", "分析中"), ("closed", "已解决")], default="processing")
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="created_groups",default=1)
    created_at = models.DateTimeField(default=timezone.now)
    # 与GenericForeignKey搭配使用，实现反向查找 bug-->chat
    chatrooms = GenericRelation(
        'chat.Chatroom',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='bug_chatroom'
    )

    def __str__(self):
        return f"{self.bug_number}"

    class Meta:
        verbose_name = "同类问题分组"
        verbose_name_plural = "同类问题分组"