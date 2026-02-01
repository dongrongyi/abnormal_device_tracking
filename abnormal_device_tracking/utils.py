import functools

# 调试用：用于追踪所有方法调用
class TraceAllMethods:
    def __getattribute__(self, name):
        attr = super().__getattribute__(name)

        if callable(attr) and not name.startswith('_') and name not in ['as_view', 'view_class']:

            @functools.wraps(attr)
            def traced_method(*args, **kwargs):
                class_name = self.__class__.__name__

                # 查找方法定义在哪个类中
                defining_class = self._find_method_origin(name)

                if defining_class and defining_class != class_name:
                    print(f"🎯 [{class_name}.{name}] (来自 {defining_class}) 开始")
                else:
                    print(f"🎯 [{class_name}.{name}] 开始")

                try:
                    result = attr(*args, **kwargs)
                    print(f"✅ [{class_name}.{name}] 完成")
                    return result
                except Exception as e:
                    print(f"❌ [{class_name}.{name}] 错误: {e}")
                    raise

            return traced_method

        return attr

    def _find_method_origin(self, method_name):
        """查找方法最初定义在哪个类中"""
        # 遍历方法解析顺序(MRO)
        for cls in self.__class__.mro():
            if (method_name in cls.__dict__ and
                    callable(getattr(cls, method_name))):
                return cls.__name__
        return None


# 专门针对Django视图的追踪Mixin
class TraceViewMixin(TraceAllMethods):
    """Django视图追踪Mixin"""
    pass


# 专门针对Django表单的追踪Mixin
class TraceFormMixin(TraceAllMethods):
    """Django表单追踪Mixin"""
    pass