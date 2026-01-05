from django.urls import path

from chat.views import ChatroomView

app_name = 'chat'
urlpatterns = [
    path('<int:process_pk>', ChatroomView.as_view(), name='chatroom'),
]