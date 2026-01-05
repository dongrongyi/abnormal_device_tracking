from django.forms import ModelForm

from problem_group.models import Bug


class BugForm(ModelForm):
    class Meta:
        model = Bug
        exclude = ('created_at','created_by','chatrooms')