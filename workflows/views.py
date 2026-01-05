# Create your views here.
# workflows/views.py
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from viewflow.workflow.models import Task
from accounts.models import Employee
from problem_group.models import Bug
from .BaseView import CustomProcessView
from .forms import ProductionTestFailForm, FAERetestForm, XRayTestForm, EngineeringAnalysisForm, MeAnalysisForm, \
    ScrappedForm, ReturnNormalFlowForm, FinalRetestForm, UploadOperationRecordForm, \
    UploadAnalysisResultForm
from .models import DeviceProcess
from devices.models import OperationRecord, Device, AnalysisResults, PositionTracking


class ProductionTestFailView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = ProductionTestFailForm  # 绑定空表单
    template_name = "workflows/production_test_fail.html"

    def get_context_data(self,** kwargs):
        context = super().get_context_data(**kwargs)
        task_pk = self.kwargs.get("task_pk")
        if task_pk:
            task = get_object_or_404(Task, pk=task_pk)
            context["task"] = task
            context["user_role"] =  [group.name for group in self.request.user.groups.all()] if self.request.user.groups.exists() else ""
            context["task_status"] = task.status  # 这里建议直接用查询到的task，避免self.task可能的延迟
        return context

    def form_valid(self, form):
        with transaction.atomic():  # 确保状态更新和业务操作在同一事务
            try:
                # 处理业务数据（创建操作记录）
                number = self.request.user.number
                operator = get_object_or_404(Employee, number=number)
                OperationRecord.objects.create(
                    process=self.process,
                    task=self.task,
                    action="设备测试3次失败，送FAE",
                    number=operator
                )
                self.task.data_submitted = True
                self.task.save()
            except Exception as e:
                import logging
                logging.error(f"创建操作记录失败: {str(e)}")
                form.add_error(None, f"记录操作失败: {str(e)}")
                return self.form_invalid(form)

        return redirect(self.get_success_url())





class FAERetestView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = FAERetestForm
    template_name = "workflows/FAE_retest.html"

    def form_valid(self, form):
        print(f"[{timezone.now()}] 表单验证通过阶段: self.process = {self.process.pk if self.process else 'None'}")
        # 表单验证通过后，通过 form.cleaned_data 获取所有字段值
        # 这是一个字典，键为表单字段名，值为用户填写的内容
        form_data = form.cleaned_data

        sn = form_data["sn"]
        hardware_version = form_data.get("hardware_version")
        project = form_data.get("project")
        software_version = form_data.get("software_version")
        config = form_data.get("config")
        fail_station = form_data.get("fail_station")
        failure_mode = form_data.get("failure_mode")
        test_link = form_data.get("test_link")
        result = form_data.get("result")

        # 获取当前用户的工号（字符串，如 "F2851370"）
        number = self.request.user.number

        # 根据工号查询 Employee 实例（找不到则返回404或处理异常）
        operator = get_object_or_404(Employee, number=number)


        # 业务处理
        device,res = Device.objects.update_or_create( # get_or_create查询sn=xxx的设备，不存在则创建，同时用default设置其他字段
            sn=sn,
            defaults={
                "hardware_version": hardware_version,
                "project": project,
                "software_version": software_version,
                "config": config,
                "test_link": test_link,
                "current_position": 'FAE',
                "failure_mode": failure_mode,
                "fail_station": fail_station,
            }
        )
        PositionTracking.objects.create(device=device, owner=operator,position="FAE",reason='产线扫修')
        operation = OperationRecord.objects.create(
            process=self.process,  # 关联当前流程
            task=self.task,  # 关联当前任务
            action='FAE复测',
            number=operator,
        )
        try:
            # 事务内保存 AnalysisResults（执行后自动提交，结果持久化）
            with transaction.atomic():
                analysis = AnalysisResults.objects.create(
                    operation=operation,  # 确保operation有值
                    process=self.process,
                    task=self.task,
                    result=result,
                    number=operator,
                    task_name='FAE_retest',
                    analysis_notes= '复测成功' if result else '复测失败'
                )
                print(f"[结果保存] AnalysisResults ID: {analysis.id} 已持久化")
                self.task.data_submitted = True
                self.task.save()
            return redirect(self.get_success_url())  # 重定向但不调用父类form_valid

        except Exception as e:
            print(f"[异常捕获] 错误详情：{str(e)}")
            return HttpResponse(f"操作异常：{str(e)}", status=500)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 查询当前流程关联的所有关键记录（跨模型）
        # 设备信息（假设一个流程对应一个设备，通过sn关联）
        device = Device.objects.filter(
            process=self.process  # 假设Device有process字段关联流程
        ).first()

        # 操作记录和分析结果（一对多或一对一关联）
        operations = OperationRecord.objects.filter(
            process=self.process,
            task=self.task
        ).order_by("-created_at")
        # 整合多模型数据为“统一条目”（每个操作记录关联设备和分析结果）
        combined_records = []
        for op in operations:
            # 查找当前操作记录对应的分析结果（假设外键关联）
            analysis = AnalysisResults.objects.filter(
                operation=op
            ).first()


            # 每条记录包含多个模型的字段（自定义需要展示的列）
            combined_records.append({
                # 来自OperationRecord的字段
                "op_id": op.id,
                "action": op.action,
                "created_at": op.created_at,
                "operator": op.number,
                # 来自AnalysisResults的字段
                "analysis_notes": analysis.analysis_notes if analysis else "",
                # 来自Device的字段（如果设备信息唯一）
                "device_sn": device.sn if device else "",
                "hardware_version": device.hardware_version if device else ""
            })

        context["combined_records"] = combined_records  # 整合后的记录列表
        context["display_columns"] = [  # 自定义要展示的列（可在视图或模板中定义）
            "created_at", "operator", "device_sn", "action", "analysis_notes"
        ]
        return context

    def get_initial(self):
        initial = super().get_initial()
        # 从流程实例中获取关联的设备SN
        if self.process and hasattr(self.process, "device") and self.process.device:
            initial["sn"] = self.process.device.sn  # 假设 Process 关联的 Device 有 sn 字段
        return initial

    def get_form_kwargs(self):
        """根据场景初始化表单数据：新增（空表单）/补充（加载已有数据）"""
        kwargs = super().get_form_kwargs()

        # 在 get_form_kwargs 中从 session 读取 operation.id
        operation_id = self.request.session.get('latest_operation_id')
        # 从已有记录加载数据到表单
        if operation_id:
            # 确保要补充的记录属于当前流程和节点
            op_record = get_object_or_404(
                OperationRecord,
                id=operation_id,
                process=self.process,
                task=self.task
            )
            # 反向查询：通过 operation 外键 + 流程/任务条件，找到 AnalysisResults
            analysis = AnalysisResults.objects.filter(
                operation=op_record,
                process=self.process,
                task=self.task
            ).first()  # 取第一条（或最新一条，按需调整）
            # 初始化表单字段（与表单类的字段对应）
            kwargs["initial"] = {
                "sn": op_record.process.device.sn,  # 从流程关联的设备获取
                "action": op_record.action,
                "analysis_notes": analysis.analysis_notes if analysis else "",
            }
        return kwargs


class XRayTestView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = XRayTestForm  # 绑定空表单
    template_name = "workflows/x-ray.html"

    def form_valid(self, form):
        form_data = form.cleaned_data

        attachment = form_data.get("attachment")
        analysis_notes = form_data.get("analysis_notes")
        result = form_data.get("result")

        number = self.request.user.number
        operator = get_object_or_404(Employee, number=number)


        operationRecord = OperationRecord.objects.create(
            process=self.process,
            task=self.task,
            action='X-ray测试',
            attachment=attachment,
            number=operator,
        )
        AnalysisResults.objects.create(
            operation=operationRecord,
            process=self.process,
            task=self.task,
            task_name="X_ray_test",
            result=result,
            analysis_notes=analysis_notes,
            number=operator,
        )
        self.task.data_submitted = True
        self.task.save()
        return redirect(self.get_success_url())  # 重定向但不调用父类form_valid




class EngineeringAnalysisView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = EngineeringAnalysisForm  # 绑定空表单
    template_name = "workflows/engineering_analysis.html"

    def get_success_url(self):
        return reverse('deviceinvestigation:engineering_analysis:execute', kwargs={'process_pk': self.process.pk,'task_pk': self.task.pk})

    def get_context_data(self, **kwargs):
        # 第一步：先调用父类的get_context_data，接收默认参数（包括form）
        context = super().get_context_data(** kwargs)
        operationRecords = OperationRecord.objects.filter(task=self.task).order_by("-created_at")
        analysisResults = AnalysisResults.objects.filter(task=self.task).order_by("-created_at")
        bug = Device.objects.get(sn=self.process.device.sn).bug
        print('sn',self.process.device.sn)
        context['operationRecords'] = operationRecords
        context['analysisResults'] = analysisResults
        context['bug'] = bug
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        action = self.request.POST.get("action")
        source = self.request.POST.get("source")
        bug = Device.objects.get(sn=self.process.device.sn).bug or None
        print("当前激活的Viewflow节点：", self.task.flow_task)

        if source == 'choices':
            if action == '上传操作记录':
                return render(request, 'workflows/upload_operation_record.html', {'form': UploadOperationRecordForm()})
            elif action == '上传分析结果/记录bug号':
                form = UploadAnalysisResultForm(task=self.task,bug=bug)
                return render(request, 'workflows/upload_analysis_result.html', {'form': form,'bug': bug})
            elif action == '确认':
                empty_form = self.get_form()  # 获取EngineeringAnalysisForm实例
                if empty_form.is_valid() and self.task.status == 'STARTED':
                    self.task.data_submitted = True
                    self.task.save()
                    return redirect('deviceinvestigation:index')
                else:
                    return self.form_invalid(empty_form)

            else:
                return redirect(self.get_success_url())
        elif source == 'operation_record':
            # 上传操作记录相关数据
            form = UploadOperationRecordForm(request.POST, request.FILES)
            if form.is_valid():
                self.upload_operation_record(form)
                return redirect(self.get_success_url())
            else:
                # 验证失败：回显表单+错误信息
                return render(request, 'workflows/upload_operation_record.html', {'form': form})
        elif source == 'analysis_result':
            # 上传分析结果相关数据
            form = UploadAnalysisResultForm(request.POST, request.FILES,task = self.task,bug=bug)
            if form.is_valid():
                self.upload_analysis_result(form)
                return redirect(self.get_success_url())
            else:
                return render(request, 'workflows/upload_analysis_result.html', {'form': form})
        else:
            return render(request,'workflows/engineering_analysis.html')


    def upload_operation_record(self, form):
        form_data = form.cleaned_data
        attachment = form_data.get("attachment")
        action = form_data.get("action")  # 获取操作动作
        number = self.request.user.number
        operator = get_object_or_404(Employee, number=number)
        OperationRecord.objects.create(
            process=self.process,
            task=self.task,
            action=action,
            attachment=attachment,
            number=operator
        )


    def upload_analysis_result(self, form):
        form_data = form.cleaned_data
        bug_number = form_data.get("bug_number") or None
        analysis_notes = form_data.get("analysis_notes")
        result = form_data.get("result")
        operation = form_data.get("operation")
        number = self.request.user.number

        operator = get_object_or_404(Employee, number=number)

        # 通过process_id获取流程实例，从中提取sn
        device_id = DeviceProcess.objects.get(id=self.process.pk if self.process else 'None').device_id
        sn = Device.objects.get(id=device_id).sn

        bug = None
        if bug_number:
            bug,res = Bug.objects.get_or_create(bug_number=bug_number)
        device = Device.objects.filter(sn=sn).first()
        if device.bug:
            pass  # bug字段有值，数据回显
        else:
            device.bug = bug  # bug字段无值，更新bug字段
            device.save()
        AnalysisResults.objects.create(
            operation=operation,
            process=self.process,
            task=self.task,
            task_name="engineering_analysis",
            result=result,
            analysis_notes=analysis_notes,
            number=operator
        )





class MeAnalysisView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = MeAnalysisForm  # 绑定空表单
    template_name = "workflows/me_analysis.html"

    def form_valid(self, form):

        form_data = form.cleaned_data

        attachment = form_data.get("attachment")
        analysis_notes = form_data.get("analysis_notes")
        action = form_data.get("action")
        result = form_data.get("result")

        number = self.request.user.number
        operator = get_object_or_404(Employee, number=number)


        operation = OperationRecord.objects.create(
            process=self.process,
            task=self.task,
            action=action,
            attachment=attachment,
            number=operator
        )
        AnalysisResults.objects.create(
            operation=operation,
            process=self.process,
            task=self.task,
            task_name="me_analysis",
            result=result,
            analysis_notes=analysis_notes,
            number=operator
        )
        self.task.data_submitted = True
        self.task.save()
        return redirect(self.get_success_url())




class FinalRetestView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = FinalRetestForm  # 绑定空表单
    template_name = "workflows/final_retest.html"

    def form_valid(self, form):

        form_data = form.cleaned_data

        result = form_data.get("result")
        number = self.request.user.number
        operator = get_object_or_404(Employee, number=number)


        operation = OperationRecord.objects.create(
            process=self.process,
            task=self.task,
            action="复测",
            number=operator,

        )
        print("operation:", operation)
        try:
            # 事务内保存 AnalysisResults（执行后自动提交，结果持久化）
            with transaction.atomic():
                analysis = AnalysisResults.objects.create(
                    operation=operation,  # 确保operation有值
                    process=self.process,
                    task=self.task,
                    result=result,
                    number=operator,
                    task_name="FAE_final_retest",
                )
                print(f"[结果保存] AnalysisResults ID: {analysis.id} 已持久化")

            saved_analysis = AnalysisResults.objects.filter(
                process=self.process,
                task=self.task
            ).first()
            if not saved_analysis:
                raise Exception("保存后查询不到 AnalysisResults 记录！")
            print(f"[验证查询] 成功查到记录：{saved_analysis}")

            self.task.data_submitted = True
            self.task.save()

            return redirect(self.get_success_url())  # 重定向但不调用父类form_valid

        except Exception as e:
            print(f"[异常捕获] 错误详情：{str(e)}")
            return HttpResponse(f"操作异常：{str(e)}", status=500)






class ScrappedView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = ScrappedForm
    template_name = "workflows/scrapped.html"

    def form_valid(self, form):

        number = self.request.user.number
        operator = get_object_or_404(Employee, number=number)

        # 自动生成操作记录（设备送FAE）
        OperationRecord.objects.create(
            process=self.process,
            action="超时无法解决，报废",
            number=operator  # 操作员工号
        )
        self.task.data_submitted = True
        self.task.save()
        return redirect(self.get_success_url())  # 重定向但不调用父类form_valid

class ReturnNormalFlowView(CustomProcessView):
    """产线测试失败（纯流转节点）视图"""
    form_class = ReturnNormalFlowForm  # 绑定空表单
    template_name = "workflows/return_normal_flow.html"
    def form_valid(self, form):
        number = self.request.user.number
        operator = get_object_or_404(Employee, number=number)
        # 自动生成操作记录（设备送FAE）
        OperationRecord.objects.create(
            process=self.process,
            action="经过讨论，复测pass,正常流线",
            number=operator  # 操作员工号
        )
        self.task.data_submitted = True
        self.task.save()

        return redirect(self.get_success_url())



