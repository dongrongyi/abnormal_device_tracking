from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.timezone import now
from django.views import View
from viewflow.workflow.flow import View as NodeView
from django.views.generic import View as BaseView, ListView, DetailView
from viewflow.workflow import Activation, STATUS
from viewflow.workflow.flow.views import UpdateProcessView, DashboardProcessListView
from viewflow.workflow.models import Process, Task
from viewflow.workflow.nodes import ViewActivation
from viewflow.workflow.signals import task_started

from accounts.models import Employee
from devices.models import OperationRecord, AnalysisResults
from workflows.models import DeviceTask, DeviceProcess


class CustomProcessView(UpdateProcessView):
    """用于提前获取process和task对象，以及兼容ModelForm和普通表单"""

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        try:
            # 初始化 process
            self.process = self.get_object()
            print(f"成功获取process: {self.process.pk}")

            # 初始化 task（从 request.activation 中获取）
            self.task = self.request.activation.task
            print(f"成功获取task: {self.task.pk}")

            print(f"[{timezone.now()}] setup阶段: self.process = {self.process.pk if self.process else 'None'}")
        except Exception as e:
            print(f"获取process或task失败: {str(e)}")
            self.process = None
            self.task = None  # 避免后续属性不存在错误

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        # 如果表单不是 ModelForm，移除 instance 参数
        if not hasattr(self.form_class, 'Meta'):
            kwargs.pop('instance', None)

        return kwargs



class DirectAssignView(View):
    """任务分配视图"""

    def get(self, request, process_pk, node_name, task_pk):   # 参数来自get请求中的URL
        task = get_object_or_404(Task, process_id=process_pk, pk=task_pk)

        available_users = Employee.objects.filter(
            department=request.user.department
        )    # 获取可assign的employee对象

        print('department:',request.user.department)

        return render(request, 'workflows/simple_assign.html', {
            'task': task,
            'available_users': available_users,
            'node_name': node_name
        })

    def post(self, request, process_pk, task_pk,**kwargs):
        task = get_object_or_404(Task, process_id=process_pk, pk=task_pk)
        user_id = request.POST.get('user_id')

        if not user_id:
            messages.error(request, "请选择一个员工")
            return redirect(request.path)

        try:
            assigned_user = Employee.objects.get(id=user_id, department=request.user.department)

            # 更新任务字段
            with task.activation() as activation:
                '''
                    activation.assign(assigned_user)相当于以下三步：
                        task.owner = assigned_user
                        task.status = 'ASSIGNED'  
                        task.save()
                '''
                activation.assign(assigned_user)
            print(f"🔹 任务 {task.pk} 绑定的节点: {task.flow_task},任务已分配给 {task.owner}")
            messages.success(request, f"任务已分配给 {task.owner}")
        except Employee.DoesNotExist:
            messages.error(request, "选择的员工不存在")

        return redirect('deviceinvestigation:index')



class BaseApprovalView(BaseView):
    """审核视图"""
    template_name = "workflows/supervisor_approval.html"  # 所有节点共用一个模板

    def get(self, request, process_pk, node_name, task_pk):
        """GET：展示审核界面（员工提交的数据+通过/驳回按钮）"""
        process = get_object_or_404(Process, pk=process_pk)
        task = get_object_or_404(Task, pk=task_pk, process=process)

        if task:
            try:
                # 获取当前节点全部的操作记录
                operation_records = OperationRecord.objects.filter(
                    process=process,
                    task=task
                ).order_by('-created_at')

                # 获取当前节点最新的一条分析结果
                analysis_result = AnalysisResults.objects.filter(
                    process=process,
                    task=task
                ).order_by('-created_at').first()

            except Exception as e:
                print(f"❌ 获取数据失败: {e}")
        else:
            print('task:',task)

        return render(request, self.template_name, {
            "task": task,
            "node_name": node_name,
            "operation_records":operation_records,  # 用于数据展示
            "analysis_result": analysis_result
        })

    def post(self, request, process_pk, node_name, task_pk):
        """处理通过/驳回逻辑"""
        task = get_object_or_404(Task, pk=task_pk, process_id=process_pk)
        action = request.POST.get("action")  # approve/reject
        deviceTask = get_object_or_404(DeviceTask, pk=task.pk)

        # 处理审核动作
        if action == "approve" and deviceTask.data_submitted == True:
            # 核心：在事务中执行 complete()，满足 Viewflow 的断言要求
            with task.activation() as activation:
                activation.complete()
            messages.success(request, f"【{node_name}】审核通过")
        elif action == "reject":
            # 驳回：回滚到待提交状态
            task.status = "ASSIGNED"   # 这里改为ASSIGNED了，但是本身就是一次post请求，会调用start方法马上变成STARTED
            deviceTask.data_submitted = False
            task.save()
            deviceTask.save()
            messages.success(request, f"【{node_name}】已驳回")

        return redirect("deviceinvestigation:index")  # 审核后返回任务列表


class CustomViewActivation(ViewActivation):
    # 该类为了符合业务需求非侵入性的修改/新增了状态转换方法
    @Activation.status.transition(
        label="Assign",
        source=STATUS.NEW,
        target=STATUS.ASSIGNED,
        permission=lambda activation, user: activation.flow_task.can_assign(
            user, activation.task
        ),
    )
    def assign(self, user):
        """Assign user to the task."""
        self.task.owner = user
        self.task.assigned = now()
        self.task.save()


    @Activation.status.transition(
        label="Upload Data",
        source=[STATUS.ASSIGNED, STATUS.STARTED],
        target=STATUS.STARTED,
        permission=lambda activation, user: activation.flow_task.can_execute(
            user, activation.task
        ),
    )
    def start(self, request):
        print('start被调用了')
        # TODO request.GET['started']
        task_started.send(sender=self.flow_class, process=self.process, task=self.task)
        self.task.started = now()
        self.task.save()


    @Activation.status.transition(
        label="Approve",
        source=STATUS.STARTED,
        target=STATUS.DONE,
        permission=lambda activation, user: True  )
    def complete(self):
        """Complete task and create next."""
        super().complete.original()
        self.activate_next()

    @Activation.status.transition(
        source=STATUS.STARTED,
        permission=lambda activation, user: activation.flow_task.can_execute(
            user, activation.task
        ),
    )
    def execute(self):
        pass


class CustomView(NodeView):
    # 让自定义的View类型的节点继承自定义的激活类
    activation_class = CustomViewActivation


class ProcessListView(ListView):
    template_name = "workflows/process_list.html"
    context_object_name = 'processes'

    def get_queryset(self):
        return DeviceProcess.objects.all()



class ProcessDetailView(DetailView):
    template_name = "workflows/process_detail.html"
    model = DeviceProcess
    context_object_name = 'process'

    # 需要的上下文数据 tasks
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process = self.get_object()
        tasks = DeviceTask.objects.filter(process=process).order_by('created')
        data_tasks = DeviceTask.objects.filter(process=process,flow_task_type='HUMAN').order_by('created')
        context['tasks'] = tasks
        context['data_tasks'] = data_tasks
        return context



