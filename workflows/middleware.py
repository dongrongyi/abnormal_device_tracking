# middleware.py
from threading import local
import re
import logging
from django.conf import settings
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import ObjectDoesNotExist
from django.apps import apps
from django.shortcuts import render
from django.utils.decorators import sync_and_async_middleware
"""
    workflows 应用的中间件配置
    核心功能：
    1. NodePermissionMiddleware：工作流节点权限核心中间件，实现「URL操作+节点部门+用户角色」的三重权限校验，适配Viewflow工作流
    2. ThreadLocalMiddleware：线程本地存储中间件，解决非视图层（模型、信号、Viewflow节点）获取当前request/user的问题
    3. 配套工具函数：AJAX判断、当前请求/用户获取、标准化权限拦截响应
    适用框架：Viewflow+AdminLTE（非纯前后端分离）
    核心依赖：Django 4.0+（兼容异步视图）、threading.local（线程隔离）
"""
# 日志器（统一记录权限相关日志）
logger = logging.getLogger('workflows.permission')


@sync_and_async_middleware  # 兼容异步视图（Django 4.0+）
class NodePermissionMiddleware:
    """
    工作流节点权限中间件
    优化点：解耦配置、规范导入、完善异常、缓存优化、标准响应、日志记录
    """
    # 预编译正则表达式（提升匹配效率）
    compiled_url_patterns = None

    def __init__(self, get_response):
        self.get_response = get_response

        # 1. 从settings读取配置（解耦硬编码）
        self.url_patterns = getattr( # getattr(x, 'y', default) = x.y，如果x.y不存在，返回default
            settings,
            'WORKFLOW_NODE_PERMISSIONS',
            {
                r'/workflows/.*/assign/$': {'operation': 'assign', 'roles': ['部门主管']},
                r'/workflows/.*/execute/$': {'operation': 'submit', 'roles': ['普通员工', '部门主管']},
                r'/workflows/.*/approve/$': {'operation': 'approve', 'roles': ['部门主管']},
                # r'/workflows/.*/(cancel|revive|unassign|undo)/$': {'operation': 'transition', 'roles': ['部门主管']}, # 这条没必要，这几个转换方法有基本的permission要求：has_manage_permission
            }
        )
        self.node_departments = getattr(
            settings,
            'WORKFLOW_NODE_DEPARTMENTS',
            {
                'production_test_fail': ['产线'],
                'FAE_initial_retest': ['FAE'],
                'X_ray_test': ['FAE'],
                'engineering_analysis': ['EE', 'SW'],
                'me_analysis': ['ME'],
                'return_normal_flow': ['Clients'],
                'FAE_final_retest': ['FAE'],
                'scrapped': ['Clients'],
            }
        )

        # 2. 预编译所有URL正则（只编译一次，提升效率）
        self._compile_url_patterns()

    def _compile_url_patterns(self):
        """预编译URL正则表达式"""
        self.compiled_url_patterns = []
        for pattern, rule in self.url_patterns.items():
            compiled_re = re.compile(pattern) # 对正则字符串做 “语法检查 + 解析转换”，把「正则表达式字符串」编译成 Python 内部的「正则表达式对象（Pattern 对象）」
            self.compiled_url_patterns.append((compiled_re, rule))

    def __call__(self, request):
        # 保留__call__但无额外逻辑（兼容中间件规范）
        response = self.get_response(request)
        return response

    def get_permission_rule(self, path):
        """使用预编译后的正则表达式对象，与path匹配，如果匹配成功，返回对应rule"""
        if not self.compiled_url_patterns:
            return None
        for compiled_re, rule in self.compiled_url_patterns:
            if compiled_re.match(path): # Pattern.match(string[, pos[, endpos]])，其中Pattern是由 re.compile() 返回的已编译正则表达式对象
                return rule
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """核心权限校验逻辑（全链路优化）"""
        # Step 1: 非workflows路径直接放行（快速返回，减少损耗）
        if not request.path.startswith('/workflows/'):
            return None

        # Step 2: 匹配URL权限规则，无规则则放行
        permission_rule = self.get_permission_rule(request.path) # {'操作名':'职级权限列表'}
        if not permission_rule:
            logger.debug("URL %s 无匹配的权限规则，直接放行", request.path)
            return None

        # Step 3: 核心权限校验（加完整异常捕获）
        try:
            # 3.1 Django 的模型懒加载——不是项目启动就导入模型，而是用到该模型时再动态获取，解决循环导入问题。中间件中使用模型 → 必须用懒加载
            DeviceTask = apps.get_model('workflows', 'DeviceTask') # apps是 Django 的应用注册表，项目启动时，Django 会自动扫描所有已注册的INSTALLED_APPS（比如你的workflows），把每个应用的模型类（比如DeviceTask）注册到这个注册表中，形成「应用名→模型名→模型类」的映射关系

            # 获取task_pk，无则拦截
            '''
                当你在urls.py中定义带参数的 URL 路由时，Django 会将 URL 中的「动态参数」解析成键值对，存入view_kwargs字典中 
                键是路由中的「参数名」，值是请求 URL 中的「实际参数值」，view_kwargs 传递给两个核心位置：
                    1、传递给中间件的process_view钩子，process_view中直接通过view_kwargs.get('参数名')获取
                    2、传递给视图
                        视图函数：view_kwargs直接解包为「关键字参数」，参数名直接作为视图函数的关键字参数传入
                            def task_approve(request, task_pk):  # 直接接收task_pk参数
                                print(task_pk)  
                                return JsonResponse({"code": 200})
                        视图类：view_kwargs被封装到self.kwargs中，视图类中通过self.kwargs.get('参数名')获取
            '''
            task_pk = view_kwargs.get('task_pk')
            if not task_pk:
                logger.warning(
                    "权限拦截 | 请求ID:%s | 路径:%s | 原因：缺少task_pk参数",
                    getattr(request, 'request_id', 'unknown'),  # 关联RequestIDMiddleware的ID
                    request.path
                )
                return self._forbidden_response(request,"缺少任务ID参数")

            # 3.3 查询任务（可加简单缓存，比如django-cacheops/本地缓存/redis缓存）
            task = DeviceTask.objects.get(pk=task_pk)
            node_name = task.flow_task.name.strip()  # 获取节点名，去空格
            required_departments = self.node_departments.get(node_name) # 获取可通行的部门列表

            # 3.4 无部门要求则放行，无部门要求就更没有职级要求
            if not required_departments:
                logger.debug(
                    "权限放行 | 请求ID:%s | 路径:%s | 节点:%s | 原因：无部门权限要求",
                    getattr(request, 'request_id', 'unknown'),
                    request.path,
                    node_name
                )
                return None

            # 3.5 调用权限检查方法
            return self._check_permission(request, required_departments, permission_rule, node_name)

        except ObjectDoesNotExist:
            logger.error(
                "权限拦截 | 请求ID:%s | 路径:%s | 原因：任务不存在（ID:%s）",
                getattr(request, 'request_id', 'unknown'),
                request.path,
                task_pk
            )
            return self._forbidden_response(request,"任务不存在或已被删除")
        except Exception as e:
            # 捕获所有异常，避免500报错
            logger.exception(
                "权限校验异常 | 请求ID:%s | 路径:%s | 异常：%s",
                getattr(request, 'request_id', 'unknown'),
                request.path,
                str(e)
            )
            return self._forbidden_response(request,"权限校验失败，请联系管理员")

    def _check_permission(self, request, required_departments, permission_rule, node_name):
        """拆分权限检查逻辑，提升可读性"""
        user = request.user
        request_id = getattr(request, 'request_id', 'unknown')

        # 1. 检查用户是否登录
        if not user.is_authenticated:
            logger.warning(
                "权限拦截 | 请求ID:%s | 路径:%s | 节点:%s | 原因：用户未登录",
                request_id, request.path, node_name
            )
            return self._forbidden_response(request,"请先登录系统")

        # 2. 检查用户部门信息
        if not hasattr(user, 'department') or not user.department:
            logger.warning(
                "权限拦截 | 请求ID:%s | 路径:%s | 节点:%s | 用户:%s | 原因：用户无部门信息",
                request_id, request.path, node_name, user.username
            )
            return self._forbidden_response(request,"用户部门信息不完整，请联系管理员配置")

        # 3. 检查部门权限（统一转小写，去空格，避免大小写/空格误判）
        # 格式化用户部门和有权限的部门列表
        user_department = user.department.name.strip().lower()
        required_departments_normalized = [d.strip().lower() for d in required_departments]
        if user_department not in required_departments_normalized:
            logger.warning(
                "权限拦截 | 请求ID:%s | 路径:%s | 节点:%s | 用户:%s | 部门:%s | 要求部门:%s",
                request_id, request.path, node_name, user.username, user.department.name, required_departments
            )
            return self._forbidden_response(request,f"需要{required_departments}部门权限")

        # 4. 检查角色权限
        # 格式化所需权限列表和用户权限列表
        required_roles = permission_rule['roles'] # 获取该url(操作)对应的职级权限列表
        user_roles = [group.name.strip().lower() for group in user.groups.all()]
        required_roles_normalized = [r.strip().lower() for r in required_roles]

        if not any(role in user_roles for role in required_roles_normalized): # 没有匹配的职级权限
            logger.warning(
                "权限拦截 | 请求ID:%s | 路径:%s | 节点:%s | 用户:%s | 角色:%s | 要求角色:%s",
                request_id, request.path, node_name, user.username, user_roles, required_roles
            )
            return self._forbidden_response(request,f"需要{required_roles}角色权限")

        # 所有权限校验通过
        logger.info(
            "权限放行 | 请求ID:%s | 路径:%s | 节点:%s | 用户:%s | 部门:%s | 角色:%s",
            request_id, request.path, node_name, user.username, user.department.name, user_roles
        )
        return None

    def _forbidden_response(self, request, message):  # 添加 request 参数
        """统一返回标准化响应（兼容前后端分离）"""
        # 判断是否是AJAX/JSON请求，返回对应格式
        if request_is_ajax(request):
            return JsonResponse({
                'code': 403,
                'message': message,
                'success': False
            }, status=403)
        return render(request, 'workflows/403.html', {
            'message': message,
            'user': request.user,
            'path': request.path,
        }, status=403)

# 辅助函数：判断是否是AJAX/JSON请求
def request_is_ajax(request):
    return request.method == 'POST' and request.META.get('CONTENT_TYPE', '').startswith('application/x-www-form-urlencoded')




'''
前提：
    Django 的默认规则是：只有「视图、中间件、装饰器」能直接拿到 request 对象（因为这些是请求处理的直接环节，request 会作为参数传入），
    但在工具函数、模型方法、Django 信号、Viewflow 工作流节点逻辑等「非视图层代码」中，若想获取当前请求的 request/user，默认只能通过层层传参的方式实现
    Django 是多线程运行的 Web 框架，每个 HTTP 请求都会被分配一个独立的线程处理，请求处理完成后线程销毁（或复用，但数据会清空）。
原理：
    threading.local()会创建一个线程本地存储对象，这个对象的特点是：每个线程对它的操作都是独立的，线程 A 存的属性，线程 B 看不到，
    不会出现多个请求的数据串扰，是多线程环境下 “安全存全局数据” 的核心工具
'''
# 通过线程局部变量的方式解决model层无法获取当前登录用户的问题, 在DeviceTask model的custom_actions方法中被使用
_thread_locals = local() # 创建一个全局的线程本地存储容器，用于存放每个请求的 request 对象

def get_current_request(): # 从线程本地存储中，获取当前线程（当前请求）存的 request 对象
    return getattr(_thread_locals, 'request', None)

def get_current_user(): # 直接获取当前登录用户
    request = get_current_request()
    if request and hasattr(request, 'user'):
        return request.user
    return None

class ThreadLocalMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request # 把request对象存入当前请求对应的线程中
        response = self.get_response(request)
        return response