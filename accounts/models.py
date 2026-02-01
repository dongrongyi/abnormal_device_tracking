from django.contrib.auth.models import AbstractUser
from django.db import models



# Create your models here.
'''
1、员工信息表Employee（工号、姓名、所属部门ID、邮箱）
2、角色表（ID、角色名、权限） 这个直接用django内置的Group model
3、用户-角色关联表（ID、工号、角色ID） 这个不需要，django内置的user model的groups字段即可实现多对多关系
'''
class Employee(AbstractUser):
    # 保留 AbstractUser 的所有字段（username, email, password 等）
    '''
    默认字段：
        username  CharField	用户名（唯一），长度 150 字符以内，可包含字母、数字、@/./+/-/_，本项目中存储用户英文名
        email	EmailField	邮箱地址（默认可为空）
        password	CharField	密码（存储加密后的哈希值，不存储明文）
        is_active	BooleanField	是否激活（默认 True，未激活用户无法登录）
        is_staff	BooleanField	是否为管理员（默认 False，True 表示可登录 Django Admin 后台）
        is_superuser	BooleanField	是否为超级用户（默认 False，拥有所有权限）
        groups	ManyToManyField	关联用户组（Group 模型），用于批量分配权限
        user_permissions	ManyToManyField	关联用户单独拥有的权限（Permission 模型）
        last_login	DateTimeField	最后一次登录时间（可为空，用户未登录过时为 None）
        date_joined	DateTimeField	用户注册 / 创建时间（自动设置为创建记录时的时间）
    '''

    email = models.EmailField(unique=True)  # 添加 unique=True，确保邮箱唯一
    number = models.CharField(max_length=10,unique=True)
    name = models.CharField(max_length=10) # 中文名
    department = models.ForeignKey(
        'departments.Department',
        on_delete=models.CASCADE,
        related_name='employees',
        null=True,  # 数据库层面允许该字段为 NULL
        blank=True  # 表单层面允许该字段为空（比如 admin 后台）
    )

    def __str__(self):
        return f"{self.number} - {self.username}"

    class Meta:
        verbose_name = "员工"
        verbose_name_plural = "员工列表"

