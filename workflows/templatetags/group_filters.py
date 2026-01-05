from django import template

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """判断用户是否属于指定组"""
    return user.groups.filter(name=group_name).exists()