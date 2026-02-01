import logging

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.timezone import now
from viewflow.workflow.flow import View as NodeView
from django.views.generic import View, ListView, DetailView
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

    '''
        重写setup()的原因：
            viewflow机制本身提供了一个get_object方法来返回process，还提供了get和post方法来调用get_object方法，
            也就是说当我们发出一个get请求时，它内部会默认调用get方法来调用get_object，这也就是所谓的第一次访问时获取process，
            但实际上get请求发出时调用的第一个方法并不是get方法，可能在其它方法中就已经访问了process属性，就会有object has no attribute 'process'这样的报错，
            所以setup方法的作用就在于在最开始就给self.process和self.task赋值，这样的话视图中的任何方法都可以直接访问process(tips:Django在视图类中引入了setup方法，
            它会在dispatch方法之前被调用，是在请求处理的最开始被调用的)。如果注释setup()方法，提交表单数据时会报错：'ProductionTestFailView' object has no attribute 'process。
    '''

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            # 初始化 process
            process_pk = self.kwargs.get('process_pk')
            self.process = DeviceProcess.objects.get(pk=process_pk)
            print(f"成功获取process: {self.process.pk}")
            # 初始化 task（从 request.activation 中获取）
            self.task = self.request.activation.task
            print(f"成功获取task: {self.task.pk}")
            print(f"[{timezone.now()}] setup阶段: self.process = {self.process.pk if self.process else 'None'}")
        except Exception as e:
            print(f"获取process或task失败: {str(e)}")
            self.process = None
            self.task = None  # 避免后续属性不存在错误

    '''
         重写get_form_kwargs()的原因：
            forms.Form的基类的__init__方法中不能接收instance参数，forms.ModelForm的基类的__init__方法中可以接收instance参数，
            但是UpdateProcessView的父类ModelFormMixin定义的的get_form_kwargs方法中却传入了instance参数，因此需要进行处理。
            如果注释get_form_kwargs方法，在请求普通表单（继承自forms.Form）时会报错。
    '''

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # 如果表单不是 ModelForm，移除 instance 参数
        if not hasattr(self.form_class, 'Meta'):
            kwargs.pop('instance', None)
        return kwargs

logger = logging.getLogger(__name__)

class DirectAssignView(View): # 简单CRUD操作 + 特定业务逻辑的场景，继承View是最直接、最清晰的选择
    """任务分配视图"""

    def get(self, request, process_pk, node_name, task_pk):   # 参数来自get请求中的URL
        '''
            Django通过URL匹配提取参数，dispatch方法将这些参数作为关键字参数传递给get/post方法。可以通过get/post方法的关键字参数直接接收，也可以不传入参数，直接通过self.kwargs字典获取，例如
                def get(self, request):  # 不定义参数
                    process_pk = self.kwargs.get('process_pk')
        '''
        task = get_object_or_404(Task, process_id=process_pk, pk=task_pk)

        available_users = Employee.objects.filter(
            department=request.user.department
        )    # 获取可assign的employee对象

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
                    用上下文管理器with task.activation() as activation来创建一个activation对象（activation()方法中通过锁机制保证当前时刻当前流程的activation唯一，
                    需要注意的是，Activation 是操作执行器，不需要在整个任务生命周期中保持同一个实例，只要同一时刻唯一操作者即可），即可实现操作的原子化和防止并发操作导致的数据竞争
                '''
                '''
                    activation.assign(assigned_user)相当于以下三步：
                        task.owner = assigned_user
                        task.status = 'ASSIGNED'  
                        task.save()
                '''
                activation.assign(assigned_user)
            logging.info(f"🔹 任务 {task.pk} 绑定的节点: {task.flow_task},任务已分配给 {task.owner}")
            messages.success(request, f"任务已分配给 {task.owner}")
        except Employee.DoesNotExist:
            messages.error(request, "选择的员工不存在")
        return redirect('deviceinvestigation:index')



class BaseApprovalView(View):
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
                activation.complete() # 把当前task status改为done，并创建下一个task/流转到下一节点
            messages.success(request, f"【{node_name}】审核通过")
        elif action == "reject":
            # 驳回：回滚到待提交状态
            task.status = "ASSIGNED"   # 这里改为ASSIGNED了，但是本身就是一次post请求，会调用start方法马上变成STARTED
            deviceTask.data_submitted = False
            task.save()
            deviceTask.save()
            messages.success(request, f"【{node_name}】已驳回")

        return redirect("deviceinvestigation:index")  # 审核后返回任务列表

def is_data_submitted(task):
    deviceTask = get_object_or_404(DeviceTask, pk=task.pk)
    return deviceTask.data_submitted


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
        conditions=[lambda activation: is_data_submitted(activation.task) == False], # data_submitted为false才可以进行该转换
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
        conditions=[lambda activation: is_data_submitted(activation.task) == True], # data_submitted为true才可以进行该转换
        permission=lambda activation, user: True  # 必须配置，否则permission=default，直接返回False
    )
    def complete(self):
        """Complete task and create next."""
        super().complete.original()
        self.activate_next()


    @Activation.status.transition(
        source=STATUS.STARTED,
        permission=lambda activation, user: False
    )
    def execute(self):
        """不符合业务逻辑，禁用execute转换"""
        raise NotImplementedError("execute方法已被禁用")


class CustomView(NodeView):
    # 让自定义的View类型的节点继承自定义的激活类
    activation_class = CustomViewActivation


# ProcessListView是针对DeviceProcess写的CRUD的列表查询操作
class ProcessListView(ListView):
    template_name = "workflows/process_list.html"
    context_object_name = 'processes'
    model = DeviceProcess
    paginate_by = 10


# ProcessDetailView是针对DeviceProcess写的CRUD的单个查询操作
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
        context['tasks'] = tasks # 全部节点
        context['data_tasks'] = data_tasks # 数据节点
        return context



