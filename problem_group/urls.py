from django.urls import path

from problem_group.views import BugListView, BugDetailView, BugUpdateView, BugCreateView

app_name = 'problem_group'
urlpatterns = [
    # bug列表、单个bug信息查询、修改bug信息、新增bug
    path('', BugListView.as_view(), name='bug_list'),
    path('<int:pk>',BugDetailView.as_view(), name='bug_detail'),
    path('<int:pk>/update',BugUpdateView.as_view(), name='bug_update'),
    path('create',BugCreateView.as_view(), name='bug_create'),
]