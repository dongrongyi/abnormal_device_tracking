# Create your views here.
# workflows/views.py
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.generic import FormView
from viewflow.workflow.flow.views import CreateProcessView

from devices.forms import DeviceForm
from devices.models import Device, OperationRecord, AnalysisResults
from problem_group.models import Bug
from .BaseView import CustomProcessView
from .forms import DeviceStartForm, ProductionTestFailForm, FAERetestForm, XRayTestForm, EngineeringAnalysisForm, \
    UploadOperationRecordForm, UploadAnalysisResultForm, MeAnalysisForm, FinalRetestForm, ScrappedForm, \
    ReturnNormalFlowForm


class StartProcessView(CreateProcessView):
    form_class = DeviceStartForm
    '''
        该视图类需要完成的事
            将前面创建的device实例存到process.device中，process是表单的save方法中创建的实例
    '''
    def form_valid(self, form):
        device = form.cleaned_data['device']
        form.instance.device = device
        return super().form_valid(form) # 父类会完成instance.save()操作



class ProductionTestFailView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    # 该视图要做的创建一条操作记录并更新task.data_submmitted
    form_class = ProductionTestFailForm
    template_name = 'workflows/production_test_fail.html'

    def form_valid(self, form):
        current_user = self.request.user
        device = self.process.device
        with transaction.atomic():
            OperationRecord.objects.create(
                action = f'{device.sn}线上同一个测站测试fail三次',
                number = current_user,
                process = self.process,
                task = self.task,
            )
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())






class FAERetestView(CustomProcessView):
    form_class = FAERetestForm

    """FAE retest节点视图"""
    '''
    该视图中要做的事情：
        1、get请求时回显device数据   表单绑定的就是device model，但是默认的get_object逻辑是用URL中的id获取对象，但URL中只有process_id和task_id，所以要重写get_object逻辑
        2、根据用户所填的信息更新device实例字段
        3、根据用户的复测结果创建一条操作记录和一条分析结果
        4、更新task.data_submmitted
    '''
    def get_object(self):
        return self.process.device  # 返回当前process对应的device实例，实现数据回显和save的自动更新

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        result = cleaned_data['result']
        with transaction.atomic():
            form.instance.current_position = 'FAE'
            form.save()
            operation = OperationRecord.objects.create(
                process = self.process,
                task = self.task,
                action = 'FAE复测',
                number = self.request.user,
            )
            AnalysisResults.objects.create(
                process = self.process,
                task = self.task,
                operation = operation,
                number = self.request.user,
                result = result,
            )
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())





class XRayTestView(CustomProcessView):
    form_class = XRayTestForm

    """X-ray-test节点视图"""
    '''
        该节点要做的事情：
            1、上传一条操作记录
            2、上传一条分析结果(父类的save方法创建了一个AnalysisResults对象，并保存了'analysis_notes','result'这两个字段)
            3、更新self.task.data_submitted = True
    '''
    def get_object(self):  # 避免UpdateView的get_object绑定process作为要更新的实例
        # 因为UpdateView）会把 get_object () 的返回值传给表单的 instance 参数，从而影响ModelForm的save()行为
        return None

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        with transaction.atomic():
            operation = OperationRecord.objects.create(
                process = self.process,
                task = self.task,
                action = 'X-ray test',
                number = self.request.user,
                attachment = cleaned_data['attachment'],
            )
            form.instance.process = self.process
            form.instance.task = self.task
            form.instance.operation = operation
            form.instance.number = self.request.user
            form.save()
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())


class EngineeringAnalysisView(CustomProcessView):
    """工程团队分析节点视图"""
    '''
        该视图需要做的事情：
            1、get请求时，展示一个表单，表单中包含三个按钮，分别对应不同的操作，因为该节点支持多轮的数据上传；还要展示当前节点已有的操作记录和分析结果
                上传操作记录  --> 跳到UploadOperationRecordForm表单渲染的模板页
                上传分析结果/记录bug号  --> 跳到UploadOperationRecordForm表单渲染的模板页
                确认 --> 表示所有的数据提交已完成，修改self.task.data_submitted = True
            2、post请求时，
                提交UploadOperationRecordForm表单，新增一条操作记录
                提交UploadAnalysisResultForm表单，新增一条分析结果/更新bug号
                点击确认时，修改self.task.data_submitted = True（推动流程）
    '''
    template_name = 'workflows/engineering_analysis.html'
    form_class = EngineeringAnalysisForm

    def post(self, request, *args, **kwargs):
        source = self.request.POST.get("source")
        action = self.request.POST.get("action")
        instance = self.get_object()  # 需要传递instance给表单，实现表单的save逻辑
        if source == 'choices': # 来自三个按钮之一
            if action == '上传操作记录':
                return render(request, 'workflows/upload_operation_record.html',{'form': UploadOperationRecordForm()})
            elif action == '上传分析结果/记录bug号':
                return render(request, 'workflows/upload_analysis_result.html',{'form': UploadAnalysisResultForm(task=self.task,instance=instance)})
            elif action == '确认':
                self.task.data_submitted = True
                self.task.save()
            else:
                pass
        elif source == 'operation_record':
            # 提交了操作记录，进行数据保存处理
            form = UploadOperationRecordForm(request.POST)
            if form.is_valid():
                self.upload_operation_record(form)
            else:
                return self.form_invalid(form)
        elif source == 'analysis_result':
            # 提交了分析结果，进行数据保存处理
            form = UploadAnalysisResultForm(request.POST, task=self.task,instance=instance)
            if form.is_valid():
                self.upload_analysis_result(form)
                form.save()  # 调用表单save，并且return redirect(self.get_success_url())
            else:
                return self.form_invalid(form)
        return redirect(self.get_success_url())


    # 重写form_invalid：处理表单验证失败的逻辑
    def form_invalid(self, form):
        """
        表单验证失败时调用：
        1. 打印错误信息到控制台（调试用）
        2. 返回带错误的表单页面（前端展示）
        """
        # ========== 1. 打印错误信息（调试用，多种格式可选） ==========
        print("===== 表单验证错误（form_invalid） =====")
        # 格式1：HTML格式的错误字典（适合前端展示）
        print("错误信息（HTML格式）：", form.errors)
        # 格式2：结构化错误（列表+异常，适合调试）
        print("错误信息（结构化）：", form.errors.as_data())
        # 格式3：JSON格式（适合AJAX请求）
        print("错误信息（JSON格式）：", form.errors.as_json())
        # 格式4：单个字段的错误（精准调试）
        for field in form.fields:
            if field in form.errors:
                print(f"字段【{field}】的错误：", form.errors[field])
        return render(self.request, self.template_name, {'form': form})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        operationRecords = OperationRecord.objects.filter(task=self.task).order_by('created_at')
        analysisResults = AnalysisResults.objects.filter(task=self.task).order_by('created_at')
        context['operationRecords'] = operationRecords
        context['analysisResults'] = analysisResults
        try:
            bug = self.get_object().bug
        except Exception as e:
            bug = None
        context['bug'] = bug
        return context

    def get_object(self):
        return self.process.device

    def upload_operation_record(self,form):
        form.instance.process = self.process
        form.instance.task = self.task
        form.instance.number = self.request.user
        form.save()


    def upload_analysis_result(self,form):
        # 除了device的bug字段可以自动实现数据回显和更新，其他字段都要手动处理 operation、analysis_notes、result
        cleaned_data = form.cleaned_data
        AnalysisResults.objects.create(
            process = self.process,
            task = self.task,
            operation = cleaned_data['operation'],
            number = self.request.user,
            analysis_notes = cleaned_data['analysis_notes'],
            result = cleaned_data['result'],
        )




class MeAnalysisView(CustomProcessView):
    '''
        该视图类中需要做的事：
            1、上传一条操作记录
            2、上传一条分析结果
            3、更新task.data_submitted = True
    '''
    template_name = 'workflows/me_analysis.html'
    form_class = MeAnalysisForm

    def get_object(self):
        return None # 避免 Viewflow 基类的UpdateView绑定错误实例,因为url中的pk是process和task的

    def form_valid(self, form):
        with transaction.atomic():
            operation = OperationRecord.objects.create(
                process = self.process,
                task = self.task,
                action = form.cleaned_data['action'],
                number = self.request.user,
                attachment = form.cleaned_data['attachment'],
            )
            form.instance.process = self.process
            form.instance.task = self.task
            form.instance.operation = operation
            form.instance.number = self.request.user
            form.instance.save()
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())





class FinalRetestView(CustomProcessView):
    '''
        该视图需要做的操作：
            1、上传一条操作记录
            2、上传一条分析结果
            3、更新task.data_submitted = True
    '''

    template_name = 'workflows/final_retest.html'
    form_class = FinalRetestForm
    def get_object(self):
        return None # 避免 Viewflow 基类的UpdateView绑定错误实例,因为url中的pk是process和task的
    def form_valid(self, form):
        with transaction.atomic():
            operation = OperationRecord.objects.create(
                process = self.process,
                task = self.task,
                action = '回到产线前的复测',
                number = self.request.user,
            )
            if form.cleaned_data['result']:
                form.instance.analysis_notes = '复测pass'
            else:
                form.instance.analysis_notes = '复测fail'
            form.instance.process = self.process
            form.instance.task = self.task
            form.instance.operation = operation
            form.instance.number = self.request.user
            form.instance.save()
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())






class ScrappedView(CustomProcessView):
    '''
        该视图要做的事情：
            1、渲染一个空表单，无需处理任何字段
            2、创建一条报废的操作记录
            3、更新task.data_submitted = True
    '''
    template_name = 'workflows/scrapped.html'
    form_class = ScrappedForm
    def form_valid(self, form):
        with transaction.atomic():
            OperationRecord.objects.create(
                process = self.process,
                task = self.task,
                action = '经过客户审批，决定报废',
                number = self.request.user,
            )
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())



class ReturnNormalFlowView(CustomProcessView):
    '''
        该视图要做的事情：
            1、渲染一个空表单，无需处理任何字段
            2、创建一条返回产线的操作记录
            3、更新task.data_submitted = True
    '''
    template_name = 'workflows/return_normal_flow.html'
    form_class = ReturnNormalFlowForm
    def form_valid(self, form):
        with transaction.atomic():
            OperationRecord.objects.create(
                process = self.process,
                task = self.task,
                action = '问题已解决，经过客户同意，可以返回产线',
                number = self.request.user,
            )
            self.task.data_submitted = True
            self.task.save()
        return redirect(self.get_success_url())



