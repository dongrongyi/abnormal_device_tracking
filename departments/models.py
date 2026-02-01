from django.db import models



# Create your models here.
'''
部门信息表：部门ID、部门名称、部门主管工号、部门联系电话
'''
class Department(models.Model):
    name=models.CharField(max_length=20)
    manager_number=models.ForeignKey('accounts.Employee',on_delete=models.CASCADE,to_field='number',related_name='managed_departments')
    telephone=models.CharField(max_length=20)

    def __str__(self):
        return self.name