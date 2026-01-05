from django.test import TestCase

# Create your tests here.
from io import StringIO
from django.core.management import call_command
from django.test import TestCase


class CleanUpCommandTest(TestCase): # 测试django管理命令clean_up
    def test_command_output(self):
        out = StringIO()
        call_command("clean_up", stdout=out)
        self.assertIn('Successfully clear', out.getvalue())