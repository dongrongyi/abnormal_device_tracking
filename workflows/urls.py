# workflows/urls.py
from django.urls import path, include
from viewflow.urls import Site
from viewflow.workflow.flow.viewset import FlowViewset
from workflows.BaseView import DirectAssignView, BaseApprovalView, ProcessListView, ProcessDetailView

# 获取 FlowViewSet 的元类（解决元类冲突的关键）
FlowViewSetMeta = type(FlowViewset)

# 定义自定义元类，继承 FlowViewSet 的元类
class AutoFlowMeta(FlowViewSetMeta):  # 继承父类的元类
    """元类：自动将 ViewSet 的 flow_class 传递给父类构造函数"""
    def __new__(cls, name, bases, attrs):
        # 创建 ViewSet 类
        new_class = super().__new__(cls, name, bases, attrs)
        # 如果当前类定义了 flow_class，强制绑定到父类初始化参数
        if 'flow_class' in attrs:
            # 重写 __init__ 方法，自动传入 flow_class
            def __init__(self, **kwargs):
                super(new_class, self).__init__(
                    flow_class=attrs['flow_class'],  # 强制传递 flow_class
                    ** kwargs
                )
            new_class.__init__ = __init__
        return new_class

# 基于自定义元类定义 ViewSet，自动关联流程类
class DeviceInvestigationFlowViewSet(FlowViewset, metaclass=AutoFlowMeta):
    # 只需定义 flow_class，元类会自动处理参数传递
    from .flows import DeviceInvestigationFlow
    flow_class = DeviceInvestigationFlow



# 初始化 Site 并修复 viewsets
site = Site()
if site.viewsets is None:
    site.viewsets = []

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
