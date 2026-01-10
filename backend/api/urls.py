from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatViewSet, chat_stream

router = DefaultRouter()
router.register(r"chats", ChatViewSet, basename="chat")

urlpatterns = [
    # ✅ put stream FIRST so it wins
    path("chats/<int:chat_id>/stream/", chat_stream, name="chat-stream"),

    # router LAST
    path("", include(router.urls)),
]
