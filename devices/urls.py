from devices import views
from django.urls import path

from devices.views import DeviceListView, DeviceDetailView, DeviceUpdateView, PositionCreateView, PositionListView, \
    PositionUpdateView

app_name = 'devices'
urlpatterns = [
    # 该路由文件中所有的pk都是device_pk
    # device model相关
    path('', DeviceListView.as_view(), name='device_list'), # 设备列表
    path('<int:pk>',DeviceDetailView.as_view(), name='device_detail'), # 设备详情
    path('<int:pk>/update',DeviceUpdateView.as_view(), name='device_update'),  # 设备更新

    # PositionTracking相关
    path('create',PositionCreateView.as_view(), name='position_create'),   # 新增设备的位置变更记录
    path('<int:pk>/postion_tracking',PositionListView.as_view(), name='position_tracking'),  # 查看单个设备的位置变更记录
    path('<int:pk>/change/<int:position_pk>',PositionUpdateView.as_view(), name='position_change'),  # 填错等情况

]