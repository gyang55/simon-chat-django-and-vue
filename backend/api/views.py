import os
import json
from django.http import StreamingHttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from google.genai import Client
from google.genai import types
from django.views.decorators.http import require_POST
from .models import Chat, Message
from .serializers import ChatSerializer, MessageSerializer


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

    @action(detail=True, methods=["post"], url_path="stream")
    def stream(self, request, pk=None):
        chat = get_object_or_404(Chat, pk=pk, user=request.user)

        user_text = (request.data.get("content") or "").strip()
        if not user_text:
            return Response({"detail": "content is required"}, status=400)

        # 1) Save user message
        Message.objects.create(chat=chat, role="user", content=user_text)

        # 2) Build prompt from history (simple & reliable)
        history = chat.messages.order_by("created_at").all()
        prompt_lines = []
        for m in history:
            prompt_lines.append(f"{m.role.upper()}: {m.content}")
        prompt = "\n".join(prompt_lines)

        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return Response({"detail": "GEMINI_API_KEY not set"}, status=500)

        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        client = Client(api_key=api_key)

        def sse(obj) -> str:
            return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

        def event_stream():
            assistant_parts = []
            try:
                stream = client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.7,
                    ),
                )

                for chunk in stream:
                    text = getattr(chunk, "text", None)
                    if text:
                        assistant_parts.append(text)
                        yield sse({"type": "delta", "delta": text})

                full_text = "".join(assistant_parts).strip()
                if full_text:
                    Message.objects.create(chat=chat, role="assistant", content=full_text)

                yield sse({"type": "done"})

            except Exception as e:
                yield sse({"type": "error", "message": str(e)})

        resp = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp
    
    
@csrf_exempt
@require_POST
def chat_stream(request, chat_id):
    payload = json.loads(request.body.decode("utf-8") or "{}")
    user_text = payload.get("content", "")
    client = Client()
    def gen():
        # Stream Gemini response in chunks :contentReference[oaicite:3]{index=3}
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-flash",
            contents=user_text,
        ):
            if getattr(chunk, "text", None):
                yield f"data: {chunk.text}\n\n"

        yield "data: [DONE]\n\n"

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp

