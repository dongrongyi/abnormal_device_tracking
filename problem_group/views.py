from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import DetailView, UpdateView, CreateView, ListView

from problem_group.forms import BugForm
from problem_group.models import Bug


# Create your views here.
class BugListView(ListView):
    template_name = 'bug/bug_list.html'
    context_object_name = 'bugs'
    def get_queryset(self):
        return Bug.objects.all()


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
    model = Bug

    def form_valid(self, form):   # 表单中没处理created_by和created_at，所以需要重写form_valid单独处理
        form.instance.created_by = self.request.user
        form.instance.created_at = timezone.now()
        return super(BugCreateView, self).form_valid(form)

