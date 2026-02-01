from django.forms import ModelForm
from django.forms.widgets import Select

from problem_group.models import Bug


class BugForm(ModelForm):
    class Meta: # 只要表单是ModelForm且包含status字段，{{ form.status }}会自动渲染出包含model中定义的 choices 选项的下拉框
        model = Bug # 外键字段/ CharField + choice 都可以这样做
        exclude = ('created_at','created_by','chatrooms')
        widgets = {
            'status': Select(attrs={'class':'form-control'}),
        }