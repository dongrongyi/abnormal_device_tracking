from django.contrib.auth.views import LoginView, PasswordChangeView, LogoutView
from django.urls import reverse_lazy
from django.views.generic import CreateView, TemplateView
from accounts.forms import EmployeeCreationForm


# Create your views here.
class CustomLoginView(LoginView): # 主要在AuthenticationForm.clean()中处理验证逻辑
    template_name = 'accounts/login.html'


class RegisterView(CreateView): # 该类中真正实现注册信息存储的是django\views\generic\edit.py中的ModelFormMixin类的form_valid方法，form_valid方法中调用了表单的save方法，该方法实现信息的存储，但是我在我自定义的表单中重写了save方法，所以它会调用我重写的save方法
    form_class = EmployeeCreationForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:login")  # 注册成功后跳转到登录



class ForgetPasswordView(TemplateView):
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
    template_name = 'accounts/login.html'


class UpdatePasswordView(PasswordChangeView):
    success_url = reverse_lazy("accounts:login")


