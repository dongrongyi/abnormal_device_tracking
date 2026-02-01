# workflows/urls.py
from django.urls import path, include
from viewflow.urls import Site
from viewflow.workflow.flow.viewset import FlowViewset
from workflows.BaseView import DirectAssignView, BaseApprovalView, ProcessListView, ProcessDetailView
from workflows.flows import DeviceInvestigationFlow


class DeviceInvestigationFlowViewSet(FlowViewset):
    # 定义流程类属性
    flow_class = DeviceInvestigationFlow
    '''
        FlowViewset是viewflow的默认视图集，由于viewflow自身业务的硬约束，flow_class是FlowViewset的__init__的必选参数，
        但是Django 框架的通用执行逻辑是 所有注册到路由 / 管理器的视图集类，框架都会在生成路由 / 处理第一个请求时，自动执行无参实例化，
        这样的话就会报错，所以必须重写视图集类的__init__，把类属性flow_class传递给视图集类的构造函数__init__
    '''
    def __init__(self, **kwargs):
        super().__init__(flow_class=self.flow_class, **kwargs)



# 初始化 Site 并修复 viewsets，这是viewflow的版本bug，viewflow开发人员在__init__方法里漏掉了self.viewsets = []这行初始化代码
site = Site()
if site.viewsets is None:
    site.viewsets = []

'''
     1. 绑定「流程类（flow_class）」与「视图集（FlowViewset）」
     2. 解析流程类的节点定义，生成「路由规则模板」
     3. 把「路由规则模板 + 视图集」挂载到`site`对象上
'''
site.register(DeviceInvestigationFlowViewSet)

print("注册后的 viewsets:", site.viewsets)
# 拆分 site.urls（处理 Django 版本兼容）
try:
    # 尝试解析 3 元组 (url_patterns, app_name, namespace)
    url_patterns, app_name, namespace = site.urls
except ValueError:
    # 解析 2 元组 (url_patterns, app_name)
    url_patterns, app_name = site.urls
    namespace = None



# 配置 URL 路由（包含根路径重定向）
urlpatterns = [
    # 通用分配URL（匹配所有节点）
    path(
        'deviceinvestigation/<int:process_pk>/<str:node_name>/<int:task_pk>/assign/',
        DirectAssignView.as_view(),
        name='assign'
    ),

    # 通用审核URL（匹配所有节点）
    path(
        "deviceinvestigation/<int:process_pk>/<str:node_name>/<int:task_pk>/approve/",
        BaseApprovalView.as_view(),
        name="approve"
    ),

    path(
        "deviceinvestigation/flows/",
        ProcessListView.as_view(),
        name="process_list",
    ),   # process列表，默认的视图展示数据不符合业务需求

    path(
        "deviceinvestigation/<int:pk>/",
        ProcessDetailView.as_view(),
        name="process_detail",
    ),   # process相关数据展示，默认的视图展示数据不符合业务需求

    # 包含 Viewflow 自动生成的所有流程路由，包括启动节点 --> 节点视图，一条路由即可生成
    path('', include((url_patterns, app_name), namespace=namespace))


]
