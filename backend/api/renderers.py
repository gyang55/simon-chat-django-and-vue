from rest_framework.renderers import BaseRenderer

class SSERenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "sse"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # We are returning StreamingHttpResponse, so this usually isn't used.
        # But it MUST exist so DRF content negotiation succeeds.
        return data
