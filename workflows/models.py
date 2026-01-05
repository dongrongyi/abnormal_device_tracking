from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.http import HttpResponseForbidden
from django.urls import reverse

from viewflow.workflow.models import Process as BaseProcess,Task as BaseTask

from departments.models import Department
from devices.models import Device, OperationRecord, AnalysisResults

from workflows.middleware import get_current_user

'''
DeviceProcess:device、department
DeviceTask:process、analysis_result、operation_record
'''

# Create your models here.
class DeviceProcess(BaseProcess):
    """异常设备处理的流程实例（一次流程对应一台设备的一次异常处理）"""
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name="workflow_processes",
        verbose_name="关联设备"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name="handled_processes",
        verbose_name="当前处理部门"  # 用于快速定位流程当前在哪个部门
    )
    # ✅ 添加反向查询
    chatrooms = GenericRelation(
        'chat.Chatroom',
        content_type_field='content_type',
        object_id_field='object_id',
        related_query_name='process_chatroom'
    )


    class Meta:
        verbose_name = "设备处理流程实例"
        verbose_name_plural = "设备处理流程实例列表"

    def __str__(self):
        return f"{self.device.sn} 的处理流程"

    def getCurrentNode(self):
        # 用于在process列表页展示当前process的当前处理节点
         return DeviceTask.objects.filter(
            process_id = self.pk
        ).order_by("-id").first().flow_task



class DeviceTask(BaseTask):  # 流程节点的任务实例（一次任务对应一个节点的处理动作）

    # 用于区分数据是否已提交，可审核
    data_submitted = models.BooleanField(default=False, verbose_name="是否已提交数据")

    # process详情页需要展示
    def get_operation_record(self):
        if self.flow_task.name == 'engineering_analysis':
            return OperationRecord.objects.filter(task__pk = self.pk).order_by("id")
        else:
            return OperationRecord.objects.filter(task__pk = self.pk).order_by("id").first()

    def get_analysis_result(self):
        if self.flow_task.name == 'engineering_analysis':
            return AnalysisResults.objects.filter(task__pk = self.pk).order_by("id")
        else:
            return AnalysisResults.objects.filter(task__pk = self.pk).order_by("id").first()

    @property
    def custom_actions(self):    # viewflow提供的钩子方法，定义index页的标签展示以及对应的处理路由
        """使用@property，通过线程局部变量获取用户"""
        user = get_current_user()
        user_roles = [g.name for g in user.groups.all()] # 获取当前登录的用户的用户角色  普通员工/部门主管
        actions = []

        if not user or not user.is_authenticated:    # 用户未登录
            return actions

        try:
            with self.activation() as activation:
                # 调用 activation 的方法, 获取当前可获得的转换（经过了状态校验和权限校验）
                transitions = activation.get_available_transitions(user)
                for transition in transitions:
                    label = transition.label
                    if user_roles.__contains__('部门主管'):   # 部门主管
                        if label == 'Assign':
                            # 生成对应的 URL ，Django 普通方式（需要手动指定命名空间）
                            url = reverse("assign", kwargs={
                                'process_pk': self.process_id,
                                'node_name': self.flow_task.name,
                                'task_pk': self.id
                            })
                        elif label == 'Cancel':
                            # 生成对应的 URL   ViewFlow 的方式（自动生成带命名空间的URL）
                            url = self.flow_task.reverse(
                                'cancel',
                                args=[self.process_id, self.id]
                            )
                        elif label == 'Upload Data':
                            if self.data_submitted:  # 数据已提交
                                continue
                            else:   # 数据未提交
                                url = self.flow_task.reverse(
                                    'execute',
                                    args=[self.process_id, self.id]
                                )
                        elif label == 'Unassign':
                            url = self.flow_task.reverse(
                                'unassign',
                                args=[self.process_id, self.id]
                            )
                        elif label == 'Reassign':
                            url = self.flow_task.reverse(
                                'detail',
                                args=[self.process_id, self.id]
                            )    # 这里要改
                        elif label == 'Approve':
                            if self.data_submitted:
                                # 生成对应的 URL ，Django 普通方式（需要手动指定命名空间）
                                url = reverse("approve", kwargs={
                                    'process_pk': self.process_id,
                                    'node_name': self.flow_task.name,
                                    'task_pk': self.id
                                })
                            else:
                                label = '数据待提交'
                                url = self.flow_task.reverse(
                                    'detail',
                                    args=[self.process_id, self.id]
                                )
                        elif label == 'Execute':
                            continue
                        actions.append((label, url))

                    else:   # 普通员工
                        if label == 'Assign':
                            label = '待主管分配'
                            # 生成对应的 URL ，Django 普通方式（需要手动指定命名空间）
                            url = reverse("assign", kwargs={
                                'process_pk': self.process_id,
                                'node_name': self.flow_task.name,
                                'task_pk': self.id
                            })
                        elif label == 'Upload Data':
                            if self.data_submitted:  # 数据已提交
                                continue
                            else:   # 数据未提交
                                url = self.flow_task.reverse(
                                    'execute',
                                    args=[self.process_id, self.id]
                                )
                        elif label == 'Approve':
                            if self.data_submitted:
                                label = '待主管审核'
                                # 生成对应的 URL ，Django 普通方式（需要手动指定命名空间）
                                url = reverse("approve", kwargs={
                                    'process_pk': self.process_id,
                                    'node_name': self.flow_task.name,
                                    'task_pk': self.id
                                })
                            else:
                                continue
                        else:
                            continue
                        actions.append((label, url))
        except Exception as e:
            print(f"custom_actions error: {e}")
            # 出错时返回空列表，让模板回退到默认逻辑
            return []
        return actions



class Meta:
        verbose_name = "设备处理任务"
        verbose_name_plural = "设备处理任务列表"