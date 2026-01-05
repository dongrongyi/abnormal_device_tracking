# middleware.py
from threading import local

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseForbidden
import re

class NodePermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

        # 定义URL模式与权限要求的映射
        self.url_patterns = {
            # 分配任务URL - 需要部门主管
            r'/workflows/.*/assign/$': {'operation': 'assign', 'roles': ['部门主管']},
            # 数据提交URL - 允许普通员工
            r'/workflows/.*/execute/$': {'operation': 'submit', 'roles': ['普通员工', '部门主管']},
            # 任务审核/流转URL - 需要部门主管
            r'/workflows/.*/approve/$': {'operation': 'approve', 'roles': ['部门主管']},
            # 取消/回退任务等URL - 需要部门主管
            r'/workflows/.*/(cancel|revive|unassign|undo)/$': {'operation': 'transition', 'roles': ['部门主管']},
        }

        # 节点与部门的映射
        self.node_departments = {
            'production_test_fail': ['产线'],
            'FAE_initial_retest': ['FAE'],
            'X_ray_test': ['FAE'],
            'engineering_analysis': ['EE','SW'],
            'me_analysis': ['ME'],
            'return_normal_flow': ['Clients'],
            'FAE_final_retest': ['FAE'],
            'scrapped': ['Clients'],
        }

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def get_permission_rule(self, path):
        """根据URL路径获取权限规则"""
        for pattern, rule in self.url_patterns.items():
            if re.match(pattern, path):
                return rule
        return None


    def process_view(self, request, view_func, view_args, view_kwargs):

        # step 1.只检查workflows相关的URL
        if not request.path.startswith('/workflows/'):
            return None    # 直接放行

        # step 2.检查是否是需要权限控制的URL
        permission_rule = self.get_permission_rule(request.path)
        if not permission_rule:
            return None  # 没有权限规则，直接放行

        # 通过task获取节点名称并确定所需部门
        task_pk = view_kwargs.get('task_pk')  # 检查 view_kwargs 中是否有 task_pk
        try:
            from workflows.models import DeviceTask
            task = DeviceTask.objects.get(pk=task_pk)
            node_name = task.flow_task.name  # task.flow_task.name可获取node_name
            required_department = self.node_departments.get(node_name)
        except ObjectDoesNotExist:
            return HttpResponseForbidden("任务不存在或已被删除")

        # step 3. 检查该task对应的节点是否有访问人员所在部门的要求
        if not required_department:
            return None  # 如果没有部门要求，直接放行

        # step 4.检查权限(核心)
        return self.check_permission(request, required_department, permission_rule)


    def check_permission(self, request, required_department, permission_rule):
        """检查用户权限：节点权限 + 节点内部操作权限"""
        user = request.user

        # 1.检查用户认证
        if not user.is_authenticated:
            return HttpResponseForbidden("请先登录")

        # 获取用户部门信息
        if not hasattr(user, 'department') or not user.department:
            return HttpResponseForbidden("用户部门信息不完整")

        # 2.检查部门权限
        if user.department.name not in required_department:
            print("department:", user.department.name)
            return HttpResponseForbidden(f"需要{required_department}部门权限")

        # 3.检查角色权限
        required_roles = permission_rule['roles']
        user_roles = [group.name for group in user.groups.all()]
        if not any(role in user_roles for role in required_roles):
            return HttpResponseForbidden(f"需要{required_roles}角色权限")

        # 权限检查通过
        return None


# 通过线程局部变量的方式解决model层无法获取当前登录用户的问题, 在DeviceTask model的custom_actions方法中被使用
_thread_locals = local()

def get_current_request():
    return getattr(_thread_locals, 'request', None)

def get_current_user():
    request = get_current_request()
    if request and hasattr(request, 'user'):
        return request.user
    return None

class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)
        return response