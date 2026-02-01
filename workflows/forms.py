# workflows/forms.py
from django import forms
from django.shortcuts import get_object_or_404
from sqlparse.sql import Operation

from accounts.models import Employee
from devices import models
from devices.models import OperationRecord, AnalysisResults, Device
from problem_group.models import Bug
from workflows.models import DeviceProcess, DeviceTask


class DeviceStartForm(forms.ModelForm):
    """设备启动表单 - 输入SN后自动创建设备"""
    device_sn = forms.CharField(
        label='设备sn',
        required=True,
        max_length=30,
        error_messages={"required": "sn不能为空", "max_length": "sn不能超过30位", },
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "name": "设备sn",
            "placeholder": "请输入设备sn"
        }),
    )

    def clean_device_sn(self):
        # 创建设备/拦截已存在设备的创建
        device_sn = self.cleaned_data['device_sn']
        # 创建Device对象
        device,created = Device.objects.get_or_create(sn=device_sn)
        if not created:
            raise forms.ValidationError("设备已存在")
        # 将device实例存入cleaned_data，视图直接取，省一次数据库查询
        self.cleaned_data['device'] = device
        return device_sn

    class Meta:
        model = DeviceProcess
        fields = []



class ProductionTestFailForm(forms.Form):
    """纯流转节点的空表单（无任何输入字段）"""
    # 无需定义任何字段，仅用于触发提交和CSRF验证
    pass



class FAERetestForm(forms.ModelForm):

    result = forms.ChoiceField(label='复测结果',
                               required=True,
                               choices=(("True","复测pass"),("False","复测fail"),),
                               error_messages={"required":"result不能为空"},
                               widget=forms.RadioSelect(),
                               )

    def clean_result(self):
        result = self.cleaned_data['result']
        return result == "True"    # 将字符串类型的值转化为布尔类型

    class Meta:
        model = Device
        exclude = ['bug','current_position','created_at','history']
        labels = {'sn':"设备sn",'hardware_version':'硬件版本','project':'专案名',
                  'software_version':'ROM版本','config':'config','fail_station':'fail站',
                  'failure_mode':'fail项','test_link':'测试链接'}




class XRayTestForm(forms.ModelForm):
    attachment = forms.CharField(
        label='附件/log存储路径',
        max_length=100,
        error_messages={"max_length": "长度不能超过100位", },
    )

    result = forms.ChoiceField(
        label="分析结果",
        required=True,
        choices=(
            ("True", "测试pass"),  # 对应模型的True
            ("False", "测试fail"),  # 对应模型的False
        ),
    )

    def clean_result(self):
        result = self.cleaned_data['result']
        return result == "True"    # 将字符串类型的值转化为布尔类型

    class Meta:
        model = AnalysisResults
        fields = ['analysis_notes','result']




class EngineeringAnalysisForm(forms.Form):
    pass


class UploadOperationRecordForm(forms.ModelForm):
    action = forms.CharField(
        label='进行的操作',
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    attachment = forms.CharField(
        label='附件/log存储路径',
        max_length=100,
        error_messages={"max_length": "附件/log存储路径长度不能超过100", },
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    class Meta:
        model = OperationRecord
        fields = ['action','attachment']


class UploadAnalysisResultForm(forms.ModelForm):
    # operation、analysis_notes、result
    def __init__(self,  *args, task = None, **kwargs):
        super().__init__(*args, **kwargs)
        operation_list = OperationRecord.objects.filter(task=task).order_by('created_at')
        operation_choices = [(obj.id, obj.action) for obj in operation_list]
        self.fields['operation'].choices =  [("", "请选择对应的操作记录")] + list(operation_choices)
        # 数据回显
        try:
            bug = self.instance.bug
            self.fields['bug_number'].initial = bug.bug_number
        except Exception as e:
            bug = None

    bug_number = forms.CharField(
        widget=forms.TextInput(attrs={"class": "form-control"}),
        required=False,
    )
    operation = forms.ChoiceField(
        label = '操作记录',
        required=True,
        choices=[],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    analysis_notes = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),)
    result = forms.ChoiceField(
        label="分析结果",
        required=True,  # 核心：改为必填，强制选非空的有效选项
        choices=(
            ("", "请选择"),  # 默认显示的提示项（空值，无法提交）
            ("True", "问题已解决"),
            ("False", "问题暂未解决"),
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_result(self):
        # 获取字符串类型的result，返回布尔类型的result
        result = self.cleaned_data['result']
        if not result:
            raise forms.ValidationError("请选择分析结果")
        return result == "True"

    def clean_bug_number(self):
        bug_number = self.cleaned_data['bug_number'].strip()
        self.bug = None
        if bug_number:
            self.bug,_ = Bug.objects.get_or_create(bug_number=bug_number)  # 如果不存在该bug，创建一个
        return bug_number

    def clean_operation(self):
        # 获取operation_pk，返回operation对象
        operation_pk = self.cleaned_data['operation']
        if not operation_pk:
            raise forms.ValidationError("请选择对应的操作记录")
        try:
            return OperationRecord.objects.get(pk=operation_pk)
        except OperationRecord.DoesNotExist:
            raise forms.ValidationError("选择的操作记录不存在，请刷新页面重试")

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.bug:
            instance.bug = self.bug
        if commit:
            instance.save()
        return instance

    class Meta:
        # device model的bug字段的回显和更新由ModelForm实现
        model = Device
        fields = []




class MeAnalysisForm(forms.ModelForm):
    # 需包含的字段：action、attachment、analysis_notes、result
    action = forms.CharField(
        label='进行的操作',
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    attachment = forms.CharField(
        label='附件/log存储路径',
        max_length=100,
        error_messages={"max_length": "长度不能超过100", },
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    analysis_notes = forms.CharField(widget=forms.TextInput(attrs={"class": "form-control"}),)


    result = forms.ChoiceField(
        label="分析结果",
        required=True,  # 核心：改为必填，强制选非空的有效选项
        choices=(
            ("", "请选择"),  # 默认显示的提示项（空值，无法提交）
            ("True", "问题已解决"),  # 有效选项1
            ("False", "问题无法解决"),  # 有效选项2
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_result(self):
        result = self.cleaned_data['result']
        if not result:
            raise forms.ValidationError("请选择分析结果")
        return result == "True"

    class Meta:
        model = AnalysisResults
        fields = ['action','attachment','analysis_notes', 'result']  # 虽然前两个字段不是model中的字段，但是可以通过这种方式指定模板中的展示顺序


class FinalRetestForm(forms.ModelForm):
    result = forms.ChoiceField(
        label="复测结果(返回产线前的复测)",
        required=True,  # 核心：改为必填，强制选非空的有效选项
        choices=(
            ("", "请选择"),  # 默认显示的提示项（空值，无法提交）
            ("True", "复测pass"),  # 有效选项1
            ("False", "复测fail"),  # 有效选项2
        ),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def clean_result(self):
        result = self.cleaned_data['result']
        if not result:
            raise forms.ValidationError("请选择复测结果")
        return result == "True"

    class Meta:
        model = AnalysisResults
        fields = ['result']





class ScrappedForm(forms.Form):
    """纯流转节点的空表单（无任何输入字段）"""
    # 无需定义任何字段，仅用于触发提交和CSRF验证
    pass


class ReturnNormalFlowForm(forms.Form):
    pass
