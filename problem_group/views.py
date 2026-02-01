from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, UpdateView, CreateView, ListView

from problem_group.forms import BugForm
from problem_group.models import Bug


# Create your views here.
class BugListView(ListView):
    model = Bug
    template_name = 'bug/bug_list.html'
    context_object_name = 'bugs'


class BugDetailView(DetailView):
    template_name = 'bug/bug_detail.html'
    context_object_name = 'bug'
    model = Bug


class BugUpdateView(UpdateView):
    model = Bug
    template_name = 'bug/bug_update.html'
    context_object_name = 'bug'
    form_class = BugForm
    success_url = reverse_lazy('problem_group:bug_list')




class BugCreateView(CreateView):
    template_name = 'bug/bug_create.html'
    form_class = BugForm
    success_url =  reverse_lazy('problem_group:bug_list')


    def form_valid(self, form):   # 表单中没处理created_by和created_at，所以需要重写form_valid单独处理
        '''
            实例的访问：
              - 表单层：form.instance（ModelForm的属性，指向待创建/编辑的模型实例）
              - 视图层：self.object（通用视图的属性，指向视图操作的核心模型实例）

            表单的form.instance赋值时机：
              无论 CreateView/UpdateView，只要视图调用`get_form()`实例化ModelForm，就会创建/绑定form.instance —— 核心区别：
              - CreateView：form.instance 是「全新的空实例」（未入库，无主键id，只有模型默认值）；
              - UpdateView：form.instance 是视图通过`get_object()`从数据库查到的「现有实例」（已入库，有主键id，带数据库旧值）。

            视图self.object的赋值时机:
              - CreateView 中的self.object：
                唯一赋值时机：仅在`form_valid`方法中调用`form.save()`（实例入库）后，由父类`form_valid`赋值（此前self.object为None）；
              - UpdateView 中的self.object：
                第一次赋值：视图在处理请求（GET/POST）的早期调用`get_object()`时，直接将查到的数据库现有实例赋值给self.object（此时是旧值，未保存修改）；
                第二次赋值：`form_valid`中调用`form.save()`（更新数据库）后，self.object会被更新为「最新保存的实例」（和form.instance是同一个实例）。

            tips:UpdateView 中self.object和form.instance是「同一个实例」

        '''
        form.instance.created_by = self.request.user
        form.instance.created_at = timezone.now()
        return super().form_valid(form)

