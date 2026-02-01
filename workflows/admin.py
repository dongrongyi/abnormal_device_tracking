from django.contrib import admin

from workflows.models import DeviceProcess, DeviceTask

# Register your models here.
admin.site.register(DeviceProcess)
admin.site.register(DeviceTask)

'''
tips: 在django-viewflow中，viewflow/workflow/admin.py中实现了Process model和Task model的admin注册，
当在项目settings.py的INSTALLED_APPS中添加了viewflow，Django 启动时会自动加载 Viewflow 的所有配置，包括它的 Admin 注册逻辑，
但是DeviceProcess(Process)、DeviceTask(Task)这些业务子类是不会被自动注册的
'''