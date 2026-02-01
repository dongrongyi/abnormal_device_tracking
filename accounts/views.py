from django.contrib.auth.views import LoginView, PasswordChangeView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from accounts.forms import EmployeeCreationForm
from departments.models import Department


# Create your views here.
class CustomLoginView(LoginView): # 主要在AuthenticationForm.clean()中处理验证逻辑
    template_name = 'accounts/login.html'
    # 配置兜底跳转页：当没有next参数时，登录后跳转到设备列表
    success_url = reverse_lazy('devices:device_list')


class RegisterView(CreateView): # 该类中真正实现注册信息存储的是django\views\generic\edit.py中的ModelFormMixin类的form_valid方法，form_valid方法中调用了表单的save方法，该方法实现信息的存储，但是我在我自定义的表单中重写了save方法，所以它会调用我重写的save方法
    form_class = EmployeeCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")  # 注册成功后跳转到登录
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        departments = Department.objects.all()
        context["departments"] = departments
        return context



class ForgetPasswordView(TemplateView):
    # 不实现实际的重置密码逻辑，只是展示一个模板页（让联系管理员）
    template_name = 'accounts/forgot-password.html'


class CustomLogoutView(LogoutView):  # 主要在django.contrib.auth.__init__.logout()函数中实现
    '''
    登出行为：
        ✅ 发送user_logged_out信号
        ✅ 清空会话数据（session.flush()）
        ✅ 删除会话记录（数据库/缓存）
        ✅ 重置request.user为匿名用户
        ✅ 清除浏览器中的session cookie
    '''
    '''
        LogoutView 不使用 success_url 配置跳转（因为不继承自FormView），而是按照以下顺序：
            前端传的 next 参数（比如表单中 <input type="hidden" name="next" value="{% url 'accounts:login' %}">）；
            视图的 next_page 属性（视图中的配置）；
            settings.LOGOUT_REDIRECT_URL（全局登出跳转配置）；
            默认值（/accounts/logout/，admin 登出页）
    '''
    next_page = reverse_lazy('accounts:login')


class UpdatePasswordView(PasswordChangeView):  # 具体的表单校验和密码更新由PasswordChangeForm和SetPasswordForm这两个表单实现
    template_name = 'accounts/update-password.html'
    success_url = reverse_lazy("accounts:login")


