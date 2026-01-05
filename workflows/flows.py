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
    ScrappedView, ReturnNormalFlowView, FinalRetestView


# 获取对应节点最新result
def get_latest_result(process, target_task_name):
    # 查询条件：当前流程 + 目标task_name，按创建时间倒序取最新一条
    latest_record = AnalysisResults.objects.filter(
        process=process,
        task_name=target_task_name  # 匹配硬编码的task_name
    ).order_by('-created_at').first()  # 最新记录在最前

    # 无记录时返回None（符合业务中"未明确"的定义）
    return latest_record.result if latest_record else None



class DeviceInvestigationFlow(Flow): # 当Python解释器遇到这个类定义时：Python会自动调用Flow.__init_subclass__方法
    """
    异常设备调查流程
    """
    process_class = DeviceProcess
    process_title = "异常设备处理流程"
    task_class = DeviceTask


    # 定义流程节点
    start = flow.Start( # 流程的启动节点
        flow_views.CreateProcessView.as_view( # as_view()方法将视图类实例化
            form_class=DeviceStartForm,  # 使用自定义表单
        ),
    ).Next(this.production_test_fail)



    # 产线测试节点 第一个业务节点
    production_test_fail = CustomView(
        ProductionTestFailView.as_view(
            form_class=ProductionTestFailForm,
        ),
        flow_namespace='deviceinvestigation',
        node_name='production_test_fail',
    ).Next(
        # 指定下一节点
        this.FAE_initial_retest
    )


    # 复测节点
    FAE_initial_retest = CustomView(
        FAERetestView.as_view(
            form_class=FAERetestForm
        ),
        flow_namespace='deviceinvestigation',
        node_name='FAE_initial_retest',
    ).Next(this.judge_retest_result)


    judge_retest_result = flow.If(
        lambda activation: get_latest_result(
            process=activation.process,  # activation 是实例，有 process 属性
            target_task_name="FAE_initial_retest"  # 替换为你实际的 task_id
        ),
    ).Then(this.return_normal_flow).Else(this.X_ray_test)


    # X-ray测试节点
    X_ray_test = CustomView(
        XRayTestView.as_view(
            form_class=XRayTestForm
        ),
        flow_namespace='deviceinvestigation',
        node_name='X_ray_test',
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
        flow_namespace='deviceinvestigation',
        node_name='engineering_analysis',
    ).Next(this.analysis_result)

    # 分支B：测试失败 → ME Team分析
    me_analysis = CustomView(
        MeAnalysisView.as_view(
            form_class=MeAnalysisForm
        ),
        flow_namespace='deviceinvestigation',
        node_name='me_analysis',
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
        flow_namespace='deviceinvestigation',
        node_name='FAE_final_retest',
    ).Next(this.final_retest_result)


    # 跨部门讨论后的决策节点
    # 核心判断节点：仅根据result的值分流
    # 三分支判断节点1：判断是否为pass
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
        flow_namespace='deviceinvestigation',
        node_name='scrapped',
    ).Next(this.end)

    # 返回产线节点
    return_normal_flow = CustomView(
        ReturnNormalFlowView.as_view(
            form_class=ReturnNormalFlowForm
        ),
        flow_namespace='deviceinvestigation',
        node_name='return_normal_flow',
    ).Next(this.end)

    # 结束节点
    end = flow.End()

