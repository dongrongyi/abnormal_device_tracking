from django.db import models
from simple_history.models import HistoricalRecords

from problem_group.models import Bug

# Create your models here.
'''
设备基本信息表：sn、project、hardware_version、software_version、config、fail station、failure mode、test_link、bug、status、created_at、status_update_at、history
设备操作记录表：操作记录ID、sn、storage_status、action、操作员工号、created_at、附件
设备分析结果表：设备sn、操作记录ID、员工工号、时间、分析结果
'''
class Device(models.Model):

    sn = models.CharField(max_length=30,unique=True)
    hardware_version = models.CharField(max_length=20,null=True, blank=True)
    project = models.CharField(max_length=20,null=True, blank=True)
    software_version = models.CharField(max_length=50,null=True, blank=True)
    config = models.CharField(max_length=20,null=True, blank=True)
    fail_station = models.CharField(max_length=20,null=True, blank=True)
    failure_mode = models.CharField(max_length=30,null=True, blank=True)  # 具体fail的测项
    test_link = models.CharField(max_length=200,null=True, blank=True)
    bug = models.ForeignKey(Bug,on_delete=models.CASCADE,null=True, blank=True,related_name='device')
    current_position = models.CharField(max_length=50,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    def __str__(self):
        return f"{self.project} - {self.sn}"


class OperationRecord(models.Model):
    process = models.ForeignKey('workflows.DeviceProcess', on_delete=models.CASCADE,null=True, blank=True)
    task = models.ForeignKey('workflows.DeviceTask', on_delete=models.CASCADE, null=True, blank=True)
    action = models.CharField()
    number = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    attachment = models.CharField(max_length=100,
        null=True,
        blank=True,
        verbose_name="文件路径/链接")

    def __str__(self):
        return f"设备:{self.process.device.sn}, {self.number.username}的操作:{self.action}, log:{self.attachment}, 时间:{self.created_at.strftime("%Y-%m-%d %H:%M:%S")}"


class AnalysisResults(models.Model):
    process = models.ForeignKey('workflows.DeviceProcess', on_delete=models.CASCADE,null=True, blank=True)
    task = models.ForeignKey('workflows.DeviceTask', on_delete=models.CASCADE, null=True, blank=True)
    operation = models.ForeignKey('devices.OperationRecord', on_delete=models.CASCADE,help_text="⚠️ 请务必选择与“设备SN”对应的操作记录，避免关联错误！")
    number = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    analysis_notes = models.TextField()
    result = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="分析结果"
    ) # 用于分支节点的判断
    history = HistoricalRecords()



    def __str__(self):
        return f"设备:{self.process.device.sn}, {self.number.username}针对操作{self.operation.action}的分析结果{self.analysis_notes}, 时间:{self.created_at.strftime("%Y-%m-%d %H:%M:%S")}"



class PositionTracking(models.Model):
    device = models.ForeignKey('devices.Device', on_delete=models.CASCADE)
    owner = models.ForeignKey('accounts.Employee', on_delete=models.CASCADE)
    position = models.CharField(max_length=100,null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=100,null=True, blank=True)

    def __str__(self):
        return f"当前位置{self.position}"