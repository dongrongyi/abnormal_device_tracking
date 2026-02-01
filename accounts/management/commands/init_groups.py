# accounts/management/commands/init_groups.py
from django.core.management.base import BaseCommand

# 自定义django管理命令：创建权限组，也可以直接在admin后台创建，但是这样有利于生产环境创建统一的权限环境
class Command(BaseCommand):
    help = 'Creates default user groups and assigns permissions'

    def handle(self, *args, **options):
        pass