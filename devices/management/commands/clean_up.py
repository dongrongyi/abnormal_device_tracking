# 该django管理命令主要用于删除bug(没关联任何设备)
from datetime import timedelta

from django.core.management import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from problem_group.models import Bug


class Command(BaseCommand):
    help = "delete unused bugs"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='模拟运行，不实际删除，只显示统计信息'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='清理几天前创建的Bug（默认1天）'
        )
        parser.add_argument(
            '--min-devices',
            type=int,
            default=0,
            help='至少关联多少个Device才保留（默认0，即只要有关联就不删除）'
        )


    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days = options['days']
        min_devices = options['min_devices']
        self.stdout.write(self.style.NOTICE(f"===== 开始执行clean_up命令，清除{days}天前创建的未关联设备的bug ====="))
        bugs_to_delete = Bug.objects.filter(
            created_at__lt=timezone.now() - timedelta(days=days)
        ).annotate(  # 给每个bug动态添加一个字段device_count
            device_count=Count('device')
        ).filter(
            device_count__lte=min_devices  # 关联的Device数量小于等于min_devices
        )
        self.stdout.write(
            self.style.WARNING(f'{bugs_to_delete.count()}')
        )
        for bug in bugs_to_delete:
            self.stdout.write(
                self.style.WARNING(f'{bug.bug_number},{bug.created_at}')
            )
        bug_count = bugs_to_delete.count()
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[模拟运行] 将删除 {bug_count} 个未被引用的Bug"
                )
            )

            for bug in bugs_to_delete[:10]:
                self.stdout.write(f"  bug号: {bug.bug_number} (创建于: {bug.created_at})")

            if bug_count > 10:
                self.stdout.write(f"  ... 还有 {bug_count - 10} 个")
        else:
            # 确保数据一致性
            with transaction.atomic():
                for bug in bugs_to_delete:
                    if bug.device_count:
                        continue
                    else:
                        bug.delete()
                        self.stdout.write(
                            self.style.SUCCESS('Successfully delete b/"%s"' % bug.bug_number)
                        )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully clear {bug_count} unused bugs')
                )






