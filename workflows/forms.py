# workflows/forms.py
from django import forms

from accounts.models import Employee
from devices.models import OperationRecord, AnalysisResults, Device
from workflows.models import DeviceProcess


class DeviceStartForm(forms.ModelForm):
    """设备启动表单 - 输入SN后自动创建设备"""

    device_sn = forms.CharField(
        label='设备SN',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '输入设备SN或使用扫码枪扫描',
            'autofocus': 'autofocus',
            'class': 'form-control'
        })
    )

    class Meta:
        model = DeviceProcess
        fields = []  # 不包含原始字段

    def clean_device_sn(self):
        """验证设备SN并自动创建设备"""
        sn = self.cleaned_data['device_sn'].strip()

        if not sn:
            raise forms.ValidationError("设备SN不能为空")

        # 查找或创建设备
        device, created = Device.objects.get_or_create(
            sn=sn,
            defaults={
            }
        )

        if created:
            print(f"✅ 新建设备: {sn}")
        else:
            process = DeviceProcess.objects.filter(device=device).first()
            if process:
                raise forms.ValidationError("该设备已有对应process")  # 防止一个device重复创建process，如果有高并发的话，要考虑form_valid和clean双重校验
            else:
                print(f"✅ 使用已有设备: {sn}")
        return device

    def save(self, commit=True):
        """保存表单时关联设备到流程"""
        # 获取设备实例
        device = self.cleaned_data.get('device_sn')

        # 创建流程实例
        process = super().save(commit=False)
        process.device = device

        if commit:
            # 先保存 process，获得 ID
            process.save()

            # 现在 process 有 ID 了，再设置设备关联
            device.process = process
            device.save()  # 保存设备的关联关系

            print(f"✅ process: {process} {process.id} {process.status}")
            print(f"✅ device: {device.sn} 关联到 process: {process.id}")

            self.save_m2m()  # 如果有多对多关系需要保存

        return process



class ProductionTestFailForm(forms.Form):
    """纯流转节点的空表单（无任何输入字段）"""
    # 无需定义任何字段，仅用于触发提交和CSRF验证
    def save(self, commit=True):
        pass


class FAERetestForm(forms.Form):
    sn = forms.CharField(
        label="设备SN",
        max_length=50,
        required=True,
        help_text="请输入设备唯一标识SN",
        disabled=True,  # 设为禁用，用户无法编辑
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    hardware_version = forms.CharField(
        label="hardware_version",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    project = forms.CharField(
        label="project",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    software_version = forms.CharField(
        label="software_version",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    config = forms.CharField(
        label="config",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    fail_station = forms.CharField(
        label="fail_station",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    failure_mode = forms.CharField(
        label="fail测项",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    test_link = forms.CharField(
        label="test_link",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    result = forms.NullBooleanField(
        label="复测通过",
        widget=forms.RadioSelect(
            choices=[(True, "pass"), (False, "fail")]
        ),
        help_text="pass表示设备复测通过"
    )

    def save(self, commit=True):
        pass



class XRayTestForm(forms.Form):

    attachment = forms.CharField(
        label="附件链接/路径",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    analysis_notes = forms.CharField(
        label="X-ray分析结果",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "请记录复测过程和结果..."})
    )

    result = forms.NullBooleanField(
        label="X-ray结果",
        widget=forms.RadioSelect(
            choices=[(True, "pass"), (False, "fail")]
        ),
        help_text="pass表示设备不存在制程问题"
    )
    def save(self, commit=True):
        pass




class EngineeringAnalysisForm(forms.Form):
    def save(self, commit=True):
        pass

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data  #


class UploadOperationRecordForm(forms.Form):
    action = forms.CharField(
        label="action",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )
    attachment = forms.CharField(
        label="附件链接/路径",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )


class UploadAnalysisResultForm(forms.Form):
    # 获取到URL中的task_id,用户筛选当前task对应的操作记录
    def __init__(self,*args,task=None,bug=None,**kwargs):
        super().__init__(*args, **kwargs)
        self.task = task
        self.bug = bug
        if self.task:
            self.fields['operation'].queryset = OperationRecord.objects.filter(task=self.task)
        else:
            self.fields['operation'].queryset = OperationRecord.objects.none()
        if self.bug:
            self.fields['bug_number'].initial = self.bug.bug_number   # 实现bug号的数据回显
            self.fields['bug_number'].widget.attrs['disabled'] = 'disabled' # 不可编辑，需要注意的是HTML中disabled的字段不会被 POST 提交，表单验证时bug_number会被设为None，导致保存时清空原有值（或触发非空校验报错）

    def clean_bug_number(self): # clean_bug_number是Django 预留的「字段级钩子方法」—— 你需要手动定义才会生效
        # 只有字段被禁用时，才返回原有值；否则返回用户输入的新值
        if self.bug:
            return self.bug.bug_number
        return self.cleaned_data.get('bug_number', '')  # 兜底空字符串，避免None

    bug_number = forms.CharField(
        label="bug号",
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    # operation字段：从当前任务的操作记录中选择
    operation = forms.ModelChoiceField(
        queryset=OperationRecord.objects.none(),  # 初始为空，后续动态填充
        label="关联操作记录",
        empty_label="请选择操作记录（必选）",  # 明确提示
        widget=forms.Select(attrs={"class": "form-select"}),
        required=False,
        help_text="请选择本次分析对应的操作记录"
    )

    analysis_notes = forms.CharField(
        label="分析结果",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "请记录复测过程和结果..."})
    )

    result = forms.NullBooleanField(
        label="问题是否解决",
        widget=forms.RadioSelect(
            choices=[(True, "pass"), (False, "fail")]
        ),
        help_text="pass表示问题已解决，复测可pass；fail表示问题暂未解决"
    )


class MeAnalysisForm(forms.Form):
    action = forms.CharField(
        label="action",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    attachment = forms.CharField(
        label="附件链接/路径",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    # operation字段：从当前任务的操作记录中选择
    operation = forms.ModelChoiceField(
        queryset=OperationRecord.objects.none(),  # 初始为空，后续动态填充
        label="关联操作记录",
        required=False,
        empty_label="请选择操作记录（必选）",  # 明确提示
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="请选择本次分析对应的操作记录"
    )

    analysis_notes = forms.CharField(
        label="分析结果",
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "class": "form-control", "placeholder": "请记录复测过程和结果..."})
    )

    result = forms.NullBooleanField(
        label="问题是否解决",
        widget=forms.RadioSelect(
            choices=[(True, "pass"), (False, "fail")]
        ),
        help_text="pass表示问题已解决，复测可pass；fail表示问题暂未解决"
    )
    def save(self, commit=True):
        pass


class FinalRetestForm(forms.Form):

    result = forms.NullBooleanField(
        label="复测通过",
        widget=forms.RadioSelect(
            choices=[(True, "pass"), (False, "fail")]
        ),
        help_text="pass表示设备复测通过"
    )
    def save(self, commit=True):
        pass





class ScrappedForm(forms.Form):
    """纯流转节点的空表单（无任何输入字段）"""
    # 无需定义任何字段，仅用于触发提交和CSRF验证
    def save(self, commit=True):
        pass


class ReturnNormalFlowForm(forms.Form):
    """纯流转节点的空表单（无任何输入字段）"""
    def save(self, commit=True):
        pass

