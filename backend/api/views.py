from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from google.genai import Client, types
import os

from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer
from .renderers import SSERenderer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .serializers import RegisterSerializer

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response({"detail": "User created"}, status=201)

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Chat.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        chat = get_object_or_404(Chat, pk=pk, user=request.user)

        if request.method == "GET":
            qs = Message.objects.filter(chat=chat).order_by("created_at")
            return Response(MessageSerializer(qs, many=True).data)

        serializer = MessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg = Message.objects.create(
            chat=chat,
            role=serializer.validated_data["role"],
            content=serializer.validated_data["content"],
        )
        return Response(MessageSerializer(msg).data, status=201)

    @action(detail=True, methods=["post"], url_path="stream",renderer_classes=[SSERenderer],)
    def stream(self, request, pk=None):
        chat = get_object_or_404(Chat, pk=pk, user=request.user)

        user_text = (request.data.get("content") or "").strip()
        if not user_text:
            return Response({"detail": "content is required"}, status=400)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return Response({"detail": "GEMINI_API_KEY not set"}, status=500)

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = Client(api_key=api_key)

        # save user
        Message.objects.create(chat=chat, role="user", content=user_text)

        # build history prompt (simple)
        history = chat.messages.order_by("created_at").all()
        prompt = "\n".join([f"{m.role.upper()}: {m.content}" for m in history])

        def event_stream():
            assistant_parts = []
            try:
                stream = client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(temperature=0.7),
                )

                for chunk in stream:
                    text = getattr(chunk, "text", None)
                    if text:
                        assistant_parts.append(text)
                        yield f"data: {text}\n\n"   # ✅ plain text

                full_text = "".join(assistant_parts).strip()
                if full_text:
                    Message.objects.create(chat=chat, role="assistant", content=full_text)

                yield "data: [DONE]\n\n"

            except Exception as e:
                yield f"data: [ERROR] {str(e)}\n\n"
                yield "data: [DONE]\n\n"

        resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp
