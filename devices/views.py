from datetime import timedelta

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, UpdateView, CreateView

from devices.forms import DeviceForm, PositionForm
from devices.models import Device, PositionTracking
from problem_group.models import Bug


# Create your views here.


class DeviceListView(ListView):
    model = Device
    template_name = 'devices/device_list.html'
    context_object_name = 'devices'

    def get_queryset(self):
        search_query = self.request.GET.get('q', '')
        if search_query:
            # 多字段搜索
            devices = Device.objects.filter(
                Q(sn__icontains=search_query) |
                Q(project__icontains=search_query) |
                Q(hardware_version__icontains=search_query) |
                Q(failure_mode__icontains=search_query) |
                Q(bug__icontains=search_query)
            )
        else:
            devices = Device.objects.all()
        return devices


class DeviceDetailView(DetailView):
    model = Device
    template_name = 'devices/device_detail.html'
    context_object_name = 'device'







class DeviceUpdateView(UpdateView):
    model = Device
    template_name = 'devices/device_update.html'
    context_object_name = 'device'
    form_class = DeviceForm
    success_url = reverse_lazy('devices:device_list')

    # 该视图需要实现get请求时展示device_update模板页，实现数据回显；post请求时提交表单数据并更新到数据库,这部分逻辑UpdateView已经实现了
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_bugs = Bug.objects.all()
        context['all_bugs'] = all_bugs
        return context



class PositionCreateView(CreateView):
    template_name = 'devices/position_create.html'
    form_class = PositionForm
    success_url = reverse_lazy('devices:device_list')

    def form_valid(self, form):
        position = form.cleaned_data['position']
        device = form.cleaned_data['device']
        device.current_position = position
        device.save()
        return super().form_valid(form)


class PositionListView(ListView):
    context_object_name = 'positions'
    template_name = 'devices/position_list.html'

    def get_queryset(self):
        # 路由路径参数：FBV中直接作为视图函数参数接收，CBV中通过self.kwargs获取；
        # URL查询参数（?key = value）：通过request.GET.get('key')获取（注意是request.GET)
        device_pk = self.kwargs.get('pk')
        device = Device.objects.get(pk=device_pk)
        return PositionTracking.objects.filter(device=device).order_by('created_at')


class PositionUpdateView(UpdateView):
    template_name = 'devices/position_update.html'
    context_object_name = 'position'
    pk_url_kwarg = 'position_pk'   # 用于指定querySet方法中的默认主键参数名
    model = PositionTracking
    form_class = PositionForm


    def get_success_url(self):
        device_pk = self.kwargs.get('pk')
        return reverse('devices:position_tracking', kwargs={'pk': device_pk})


    def dispatch(self, request, *args, **kwargs):
        device_pk = self.kwargs.get('pk')
        # 权限校验：只有本人可进行该操作
        if not self.get_object().owner == request.user:
            messages.error(
                request,
                "只有本人可编辑！"
            )
            return redirect(reverse('devices:position_tracking', kwargs={'pk': device_pk}))

        # 时间窗口校验：是否在创建后5分钟内
        now = timezone.now()
        five_minutes_ago = now - timedelta(minutes=5)
        if self.get_object().created_at < five_minutes_ago:
            messages.error(
                request,
                "超过五分钟不可编辑！"
            )
            return redirect(reverse('devices:position_tracking', kwargs={'pk': device_pk}))
        return super().dispatch(request, *args, **kwargs)


