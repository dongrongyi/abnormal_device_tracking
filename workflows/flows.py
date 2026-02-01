# workflows/flows.py

from viewflow import this
from viewflow.workflow import Flow, flow
from viewflow.workflow.flow import views as flow_views

from abnormal_device_tracking import settings
from abnormal_device_tracking.utils import TraceViewMixin
from devices.models import OperationRecord, AnalysisResults
from .BaseView import CustomView

from .forms import ProductionTestFailForm, FAERetestForm, XRayTestForm, EngineeringAnalysisForm, MeAnalysisForm, \
    ScrappedForm, ReturnNormalFlowForm, DeviceStartForm, FinalRetestForm

from .models import DeviceProcess, DeviceTask


from .views import ProductionTestFailView, FAERetestView, XRayTestView, EngineeringAnalysisView, MeAnalysisView, \
    ScrappedView, ReturnNormalFlowView, FinalRetestView, StartProcessView


# 获取对应节点最新result
def get_latest_result(process, target_task_name):
    # 查询条件：当前流程 + 目标task_name，按创建时间倒序取最新一条
    tasks = DeviceTask.objects.filter(process=process)
    target_task = None
    for task in tasks:
        if task.flow_task.name == target_task_name:
            target_task = task
            break
    # 查询最新的AnalysisResults
    latest_record = AnalysisResults.objects.filter(
        process=process,
        task=target_task
    ).order_by('-created_at').first()
    if latest_record:
        return latest_record.result
    # 无记录时返回None（符合业务中"未明确"的定义）
    else:
        return None



class DeviceInvestigationFlow(Flow): # 当Python解释器遇到这个类定义时：Python会自动调用Flow.__init_subclass__方法
    """
    异常设备调查流程
    """
    process_class = DeviceProcess
    process_title = "异常设备处理流程"
    task_class = DeviceTask

    '''
        原生Viewflow的节点运行机制
            在原生Django-Viewflow框架中，每个工作流节点（特别是View节点）绑定一个Django视图类。当节点被激活时，Viewflow会自动生成标准URL端点：
            /{process_id}/{node_name}/{task_id}/execute/。这个绑定的视图类负责处理节点的整个完整交互流程——从展示任务详情、渲染操作表单到处理用户提交并决定流程下一步。
            框架假设一个节点对应一个主要的业务操作界面，用户在这个单一界面中完成所有可能的操作（如批准、拒绝、转交等）。
            例如，一个审批节点的视图类需要在同一个页面中根据用户角色显示不同的表单选项，通过条件判断来处理多种操作分支。Viewflow的核心设计哲学是"一个节点，
            一个处理入口"，这种集中式设计简化了流程定义，但在复杂业务场景中可能导致单个视图类承担过多职责，代码混杂多种业务逻辑。
            @property
            def view_path(self):
                return path(
                    f"<int:process_pk>/{self.name}/<int:task_pk>/execute/",
                    utils.wrap_view(self, self.view),
                    name="execute",
                )

        我的架构机制、区别及优劣分析
            在我的设备异常追踪系统中，我重构了Viewflow的交互模型：节点绑定的视图类仅处理"执行提交"这一核心操作（对应原生的execute端点），不破坏原有的节点定义结构，只是改变了execute操作的定义（不再绑定全流程，而是只绑定数据提交的操作，沿用execute的url）
            通过重写viewflow的钩子方法custom_action方法，为每个节点动态生成额外的操作菜单（assign、approve等），这些操作指向独立的专用视图。这样，一个工作流节点被拆解为多个单一职责的操作端点——assign负责任务分配，execute负责技术执行，approve负责质量审批。每个操作有独立的视图、表单和权限控制。这种架构与原生Viewflow的根本区别在于将"节点中心化"转变为"操作中心化"，将复杂的条件逻辑拆解为清晰的视图分离。
            优势：
                1) 符合单一职责原则，每个视图只处理一种业务操作，代码可维护性显著提升；
                2) 权限控制更精准，可以在视图级别实施不同的三维权限校验；
                3) 用户体验优化，不同角色获得针对性界面；
                4) 扩展性强，新增操作只需添加视图而不修改核心逻辑。
            代价：
                1) 增加了视图数量和维护点；
                2) 需要手动管理custom_action的URL生成；
                3) 对Viewflow的自动化特性有一定折损。整体而言，这是针对制造业多角色复杂审批场景的合理架构演进，在保持Viewflow状态机内核的同时，通过操作分离解决了业务复杂性带来的代码混乱问题。
    '''

    '''
        构造者模式：flows.py类似.Permission(...).Next(...).Assign(...)的链式调用是通过构造者模式实现的
            核心设计特点：
                返回self：每个配置方法都返回节点实例本身self，允许连续调用。
                配置与构造分离：节点实例化时定义核心属性，链式方法配置行为逻辑。
                关注点分离：每个链式方法只配置一个方面的行为（权限、分配、流向等）
            def Permission(self, check_func):
                """设置权限检查函数"""
                self.permission_check = check_func
                return self  # 关键：返回self实现链式调用
            def Next(self, node):
                """设置下一个节点"""
                self.next_node = node
                return self  # 关键：返回self实现链式调用
                
        需要注意的是，Permission和Next这些方法在不同的Mixin中实现(NextNodeMixin和NodePermissionMixin)，而CustomView继承自这些类
    '''

    '''
        节点名称(node.name)的完整运行机制
            来源：流程类的变量名  production_test_fail = CustomView(...)
            赋值时机和位置：流程类定义时，其父类的元类会对节点变量名进行赋值和处理
                @property
                def name(self) -> str:
                    return self.app_name
                @name.setter
                def name(self, value: str) -> None:
                    self.app_name = value
                    if not self.task_title:
                        self.task_title = value.replace("_", " ").title()
            使用位置：
                位置一 URL生成时会访问self.name(view_path方法中)
                位置二 任务显示（前端模板） 在任务列表或详情页中用node.task_title显示："Production Test Fail"
                位置三 内部引用 start.Next(this.production_test_fail)  # this对象内部使用节点名称进行查找
    '''
    '''
        流程命名空间(flow.app_name)的完整运行机制
            来源：流程类的类名DeviceInvestigationFlow
            赋值时机和位置：流程类定义时，其父类的元类会对类名进行处理(去掉Flow再转小写) "DeviceInvestigation"-->"deviceinvestigation"
                cls.app_name = strip_suffixes(cls.__name__, ["Flow"]).lower()
            使用位置
                位置一：URL反向解析命名空间 生成viewflow自带的url时，会自动解析出命名空间
                位置二：URL路径前缀
    '''

    # 定义流程节点
    start = flow.Start( # 流程的启动节点
        StartProcessView.as_view( # as_view()方法将视图类实例化
            form_class=DeviceStartForm,  # 使用自定义表单
        ),
    ).Next(this.production_test_fail)



    # 产线测试节点 第一个业务节点
    production_test_fail = CustomView(
        ProductionTestFailView.as_view(
            form_class=ProductionTestFailForm,
        ),
    ).Next(
        # 指定下一节点
        this.FAE_initial_retest
    )


    # 复测节点
    FAE_initial_retest = CustomView(
        FAERetestView.as_view(
            form_class=FAERetestForm
        ),
    ).Next(this.judge_retest_result)


    judge_retest_result = flow.If(
        lambda activation: get_latest_result(
            process=activation.process,  # activation 是实例，有 process 属性
            target_task_name="FAE_initial_retest"
        ),
    ).Then(this.return_normal_flow).Else(this.X_ray_test)


    # X-ray测试节点
    X_ray_test = CustomView(
        XRayTestView.as_view(
            form_class=XRayTestForm
        ),
    ).Next(this.judge_X_ray_result)


    # 在流程中使用这个函数
    judge_X_ray_result = flow.If(
        lambda activation: get_latest_result(
            process=activation.process,  # activation 是实例，有 process 属性
            target_task_name="X_ray_test"
        )
    ).Then(this.engineering_analysis).Else(this.me_analysis)

    # 分支A：测试通过 → 工程团队分析
    engineering_analysis = CustomView( # EE分析
        EngineeringAnalysisView.as_view(
            form_class=EngineeringAnalysisForm
        ),
    ).Next(this.analysis_result)

    # 分支B：测试失败 → ME Team分析
    me_analysis = CustomView(
        MeAnalysisView.as_view(
            form_class=MeAnalysisForm
        ),
    ).Next(this.analysis_result)

    # me_analysis / engineering_analysis的分析结果
    analysis_result = flow.If(
        # 条件：工程分析节点的最新result是否为'pass'，能解决问题
        lambda activation:
        get_latest_result(activation.process, 'engineering_analysis') == 1 or
        get_latest_result(activation.process, 'me_analysis') == 1,
    ).Then(this.FAE_final_retest).Else(this.scrapped)


    # FAE最终复测
    FAE_final_retest = CustomView(
        FinalRetestView.as_view(
            form_class=FinalRetestForm
        ),
    ).Next(this.final_retest_result)


    # 核心判断节点：仅根据result的值分流
    final_retest_result = flow.If(
        # 条件：FAE最终复测是否为'pass'
        lambda activation:
        get_latest_result(activation.process, 'FAE_final_retest') == 1
    ).Then(this.return_normal_flow).Else(this.scrapped)


    # 报废节点
    scrapped = CustomView(
        ScrappedView.as_view(
            form_class=ScrappedForm
        ),
    ).Next(this.end)

    # 返回产线节点
    return_normal_flow = CustomView(
        ReturnNormalFlowView.as_view(
            form_class=ReturnNormalFlowForm
        ),
    ).Next(this.end)

    # 结束节点
    end = flow.End()


