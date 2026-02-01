from django.contrib.auth.forms import UserCreationForm

from abnormal_device_tracking.utils import TraceFormMixin
from accounts.models import Employee


class EmployeeCreationForm(UserCreationForm):

    # 当你定义Meta类后，Django自动：
    # 1. 读取Employee模型的字段定义
    # 2. 根据模型字段类型生成对应的表单字段
    # 3. 应用模型的验证规则（如max_length、unique等）

    class Meta:
        model = Employee
        fields = ("username", "email", "number", "password1", "password2","department")

    # UserCreationForm默认只处理username和password，其他字段需要单独处理，所以要重写save
    def save(self, commit=True):
        user = super().save(commit=False)  # 利用UserCreationForm的密码处理
        user.email = self.cleaned_data["email"]
        user.number = self.cleaned_data["number"]
        user.department = self.cleaned_data["department"]
        if commit:
            user.save()
        return user
