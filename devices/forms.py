from django import forms
from django.forms import ModelForm
from django.forms.widgets import TextInput

from accounts.models import Employee
from devices.models import Device, PositionTracking
from problem_group.models import Bug


class DeviceForm(ModelForm):
    # Django 为 “关联模型的下拉选择” 设计了ModelChoiceField（专门适配 ForeignKey / 模型实例），无需手动构造choices，自动处理实例→(ID, 文本) 的转换，且支持自动验证
    bug = forms.ModelChoiceField(widget=forms.Select(attrs={'class':'form-control'}),
                                 queryset=Bug.objects.all(),
                                 empty_label='请选择对应bug'
                                 )

    class Meta:
        model = Device
        exclude = ('created_at','process')



class PositionForm(ModelForm):
    # ========== 显式定义字段类型为CharField，覆盖外键默认的ModelChoiceField ==========
    # ✅ 不显式定义表单字段 → ModelForm会「自动为外键生成默认的表单字段（ModelChoiceField）」，ModelChoiceField 的核心校验规则：提交的值必须是该字段 queryset（可选列表）中的某个选项的 value
    # ✅ 显式定义表单字段 → 会覆盖这个默认的表单字段类型，表单层的校验规则也会跟着换成你定义的字段类型的规则。

    device = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control','autofocus': True,'placeholder': '扫码/输入设备SN'}))
    owner = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control','placeholder': '扫码/输入负责人工号'}))
    class Meta:
        model = PositionTracking
        fields = ['device', 'owner', 'position', 'reason']  # 只包含需要手动输入的字段
        widgets = {
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '最多150字'}),
            'reason': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '最多150字'}),
        }

    # 校验 and 处理表单数据，返回符合数据库要求的对象
    def clean_device(self):
        device_sn = self.cleaned_data.get('device').strip() # 输入的是sn字符串
        if not device_sn:
            raise forms.ValidationError('设备sn不能为空，请扫码/输入')
        try:
            return Device.objects.get(sn=device_sn) # 返回对应的device对象
        except Device.DoesNotExist:
            raise forms.ValidationError(f'设备SN {device_sn} 不存在，请重新扫码/输入')

    # 校验 and 处理表单数据，返回符合数据库要求的对象
    def clean_owner(self):
        owner_number = self.cleaned_data.get('owner').strip() # 输入的是工号字符串
        if not owner_number:
            raise forms.ValidationError('负责人工号不能为空，请扫码/输入')
        try:
            return Employee.objects.get(number=owner_number) # 返回对应的employee对象
        except Employee.DoesNotExist:
            raise forms.ValidationError(f'负责人工号 {owner_number} 不存在，请重新扫码/输入')


