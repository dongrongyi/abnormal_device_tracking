
from django.views.generic import TemplateView

from chat.models import Chatroom, Message


# Create your views here.
# 处理基于process的聊天室
class ChatroomView(TemplateView):
    template_name = 'chat/chatroom.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        process_id = self.kwargs['process_pk']
        chatroom = Chatroom.objects.get(object_id=process_id)
        messages = Message.objects.filter(chatroom=chatroom).order_by('created_at')
        context['messages'] = messages
        context['chatroom'] = chatroom
        context['user'] = self.request.user
        return context