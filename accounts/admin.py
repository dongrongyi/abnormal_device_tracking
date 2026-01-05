from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts import models
from accounts.models import Employee


# 配置自定义用户类在admin后台的展示
@admin.register(Employee)
class EmployeeAdmin(UserAdmin):
    list_display = ('username', 'email', 'number', 'department', 'is_staff', 'is_active')
    list_filter = ('department', 'is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'number')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('Custom info', {'fields': ('number', 'department')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'email', 'number'),
        }),
    )

    ordering = ('username',)

    filter_horizontal = ('groups', 'user_permissions',)
