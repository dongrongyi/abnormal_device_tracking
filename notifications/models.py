from django.db import models



# Create your models here.
'''
邮件信息存储类：ID、发送方、接收方、邮件描述、发送时间
'''
class EmailInfo(models.Model):
       sender = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE,to_field='email',related_name='sent_emails')
       receiver = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE,to_field='email',related_name='received_emails')
       description = models.TextField() # 邮件描述信息
       created_at = models.DateTimeField(auto_now_add=True)