# abnormal_device_tracking/middleware.py
import time
import uuid
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class PerformanceMiddleware:
    """
    性能监控中间件
    监控每个请求的耗时和数据库查询次数
    """
    # 1. 初始化方法
    def __init__(self, get_response):
        # get_response：Django传入的“下一个中间件/视图函数”的引用
        # 作用：中间件是链式调用的，这个参数用来传递请求到下一个环节
        self.get_response = get_response  # 保存这个引用，供__call__方法使用
        # 知识点：__init__ 只在Django启动时执行1次，不是每个请求都执行！

    # 2. 核心方法（每个请求都会触发）
    def __call__(self, request):
        # ===== 【请求处理前】：记录初始数据 =====
        # 记录请求开始的时间戳（单位：秒，比如 1735689000.123）
        start_time = time.time()
        # 获取“当前已执行的SQL查询数量”作为初始值
        # connection.queries：Django记录的所有SQL查询列表（仅DEBUG=True时生效！）
        # len() 取列表长度 = 查询次数
        initial_query_count = len(connection.queries)

        # ===== 核心：调用后续中间件/视图，处理请求 =====
        # 把请求传递给下一个中间件（或视图），并获取响应结果
        # 这行代码是中间件的“核心链路”，前面是请求前逻辑，后面是响应后逻辑
        response = self.get_response(request)

        # ===== 【响应处理后】：计算性能数据 =====
        # 计算请求总耗时：结束时间 - 开始时间（保留3位小数）
        duration = time.time() - start_time
        # 计算本次请求的SQL查询次数：总查询数 - 初始查询数
        # （避免累计之前请求的查询，只算当前请求的）
        query_count = len(connection.queries) - initial_query_count

        # ===== 慢请求监控：耗时>1秒打警告日志 =====
        if duration > 1.0:  # 耗时超过1秒判定为慢请求
            logger.warning(
                "慢请求警告 | 路径:%s | 方法:%s | 耗时:%.3f秒 | 查询:%d次",
                request.path,    # 请求路径（比如 /workflows/1/approve/）
                request.method,  # 请求方法（GET/POST/PUT等）
                duration,        # 耗时（保留3位小数）
                query_count      # 数据库查询次数
            )

        # ===== 响应头添加性能数据（供前端/运维监控），跨端传递性能数据（后端→前端 / 运维 / 监控工具），无侵入式 =====
        # 给响应头加自定义字段：X-Request-Duration（耗时）
        response['X-Request-Duration'] = f'{duration:.3f}s'
        # 给响应头加自定义字段：X-Query-Count（查询次数）
        response['X-Query-Count'] = str(query_count)

        # ===== 返回响应 =====
        # 把响应传递给上一个中间件（或客户端）
        return response


class RequestIDMiddleware:
    """
    请求ID追踪中间件
    为每个请求生成唯一ID，便于日志追踪

    tips: 该中间件可以输出更详细的日志信息(方法、路径、真实 IP、用户等)，暂时就这样，后续在慢慢迭代
    """

    # 1. 初始化方法（和上面一样）
    def __init__(self, get_response):
        self.get_response = get_response  # 保存下一个中间件/视图的引用

    # 2. 核心方法（每个请求触发）
    def __call__(self, request):
        # ===== 【请求处理前】：生成/获取请求ID =====
        # 先尝试从请求头获取X-Request-ID（比如前端/网关传过来的ID）
        # Django会把请求头的「X-Request-ID」转成「HTTP_X_REQUEST_ID」（大写+HTTP_前缀）
        request_id = request.META.get('HTTP_X_REQUEST_ID')

        # 如果请求头没有传，自己生成一个唯一ID
        if not request_id:
            # uuid.uuid4()：生成随机的唯一UUID（比如 1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed）
            # .hex：转成32位16进制字符串（去掉横线）
            # [:16]：取前16位（简化ID长度，避免太长）
            # 加req_前缀：方便日志里识别这是请求ID
            request_id = f'req_{uuid.uuid4().hex[:16]}'
            logger.info("生成随机请求ID:%s",request_id)

        # 把请求ID绑定到request对象上
        # 后续的视图/其他中间件可以直接用 request.request_id 获取这个ID！
        request.request_id = request_id

        # ===== 打“请求开始”的日志 =====
        logger.info(
            "请求开始 | ID:%s | 路径:%s | IP:%s",
            request_id,  # 唯一请求ID
            request.path,  # 请求路径
            # REMOTE_ADDR 是客户端的IP地址，若服务器有反向代理（如Nginx），可能需要取HTTP_X_FORWARDED_FOR
            request.META.get('REMOTE_ADDR', 'unknown')
        )

        # ===== 调用后续中间件/视图 =====
        response = self.get_response(request)

        # ===== 【响应处理后】：把请求ID塞到响应头 =====
        # 前端可以从响应头里拿到 X-Request-ID，反馈给后端开发者时只需要说 “ID为req_xxx 的请求报错了”，你直接在日志里搜这个 ID，就能找到该请求的完整处理日志（包括开始时间、IP、状态码、耗时等）
        response['X-Request-ID'] = request_id # 让整个请求的 “发起→处理→响应” 链路可追溯

        # ===== 打“请求完成”的日志 =====
        logger.info(
            "请求完成 | ID:%s | 状态码:%s",
            request_id,  # 唯一请求ID
            response.status_code  # 响应状态码（200成功/403无权限/500报错等）
        )

        # ===== 返回响应 =====
        return response