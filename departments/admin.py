from django.contrib import admin

from departments.models import Department

# Register your models here.
# 配置department model在admin后台的展示效果
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'manager_number', 'telephone')
    list_filter = ('manager_number',)
    search_fields = ('name', 'manager_number__number') # 纯 ForeignKey 字段会默认根据ID查找，但默认是字符串查找，所以要对 ForeignKey关联模型的字符串字段进行查找（用双下划线__穿透关联），比如manager__username
    autocomplete_fields = ['manager_number']

    # 详情页的字段分组
    fieldsets = (
        ('部门基本信息', {
            'fields': ('name',)
        }),
        ('主管信息', {
            'fields': ('manager_number',),
            'description': "请选择该部门的主管（必须是已存在的员工）"
        }),
        ('联系电话', {
            'fields': ('telephone',)
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('name', 'manager_number', 'telephone'),
        }),
    )





