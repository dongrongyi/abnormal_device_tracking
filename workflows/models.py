from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.http import HttpResponseForbidden
from django.urls import reverse

from viewflow.workflow.models import Process as BaseProcess,Task as BaseTask

from departments.models import Department
from devices.models import OperationRecord, AnalysisResults, Device

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
    # 与GenericForeignKey搭配使用，实现反向查找 process-->chat
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

    '''
        DeviceTask和Task的区别：
            抽象基类(配置了abstract = True)只有子类表，父类没有字段，所以父类子类可以共享字段，而非抽象基类（默认）子类可以访问父类的字段，
            父类不能访问子类的字段，但父类和子类有一个pk一一对应，也就是说DeviceTask可以访问Task字段，但Task对象不能访问DeviceTask字段
    '''

    # 用于区分数据是否已提交，可审核
    data_submitted = models.BooleanField(default=False, verbose_name="是否已提交数据")

    # process详情页需要展示
    def get_operation_record(self):
        return OperationRecord.objects.filter(task__pk = self.pk).order_by("id")


    def get_analysis_result(self):
        return AnalysisResults.objects.filter(task__pk = self.pk).order_by("id")


    @property  # 方法的 “属性化封装”，使得在process_dashboard.html中调用时无需加括号
    def custom_actions(self):    # viewflow提供的钩子方法(templates\viewflow\workflow\process_dashboard.html页面提供的)，通过自定义实现去定义index页的标签展示以及对应的处理路由
        user = get_current_user() # 通过线程局部变量获取用户，（定义的中间件ThreadLocalMiddleware把request对象传到threading.local对象中）
        user_roles = [g.name for g in user.groups.all()]  # 获取当前登录的用户的用户角色  普通员工/部门主管
        actions = []

        if not user or not user.is_authenticated:    # 用户未登录
            return actions # 不能进行任何操作

        try:
            with self.activation() as activation:
                # 调用 activation 的方法, 获取当前可获得的转换（经过了状态校验和权限校验），其中权限校验主要是校验节点的permission参数
                transitions = activation.get_available_transitions(user)
                print(transitions,self.pk,'transitions')
                for transition in transitions:
                    label = transition.label
                    if label == 'Assign':
                        # 生成对应的 URL ，Django 普通方式（需要手动指定命名空间）
                        url = reverse("assign", kwargs={
                            'process_pk': self.process_id,
                            'node_name': self.flow_task.name,
                            'task_pk': self.id
                        })
                        if '部门主管' not in user_roles:
                            label = '待主管分配'
                    elif label == 'Cancel':
                        # 生成对应的 URL   ViewFlow 的方式（自动生成带命名空间的URL）
                        url = self.flow_task.reverse(
                            'cancel',
                            args=[self.process_id, self.id]
                        )
                    elif label == 'Upload Data':
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
                        # 这里要改,viewflow中虽然提供了名为reassign的状态转换函数，但并没有处理reassign的路由
                        continue
                        # url = self.flow_task.reverse(
                        #     'detail',
                        #     args=[self.process_id, self.id]
                        # )
                    elif label == 'Approve':
                        # 生成对应的 URL ，Django 普通方式（需要手动指定命名空间）
                        url = reverse("approve", kwargs={
                            'process_pk': self.process_id,
                            'node_name': self.flow_task.name,
                            'task_pk': self.id
                        })
                        if '部门主管' not in user_roles: # 普通员工
                            label = '待主管审核'
                    else:
                        continue
                    actions.append((label, url))
                print('actions',actions,self.data_submitted)
        except Exception as e:
            print(f"custom_actions error: {e}")
            # 出错时返回空列表，让模板回退到默认逻辑
        return actions





class Meta:
        verbose_name = "设备处理任务"
        verbose_name_plural = "设备处理任务列表"