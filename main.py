import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성
# 최신 SDK에서는 생성 시점에 server를 주입하지 않고 handle_sse에서 주입하거나
# 내부적으로 처리하도록 설계되어 있습니다.
sse = SseServerTransport("/messages")

# 2. 핸들러 구현 (가장 안전한 방식)
async def handle_sse(request):
    # Starlette Request 객체에서 직접 scope, receive, send를 추출하여 전달합니다.
    # 이것이 AttributeError: 'Request' object has no attribute 'send'를 고치는 유일한 방법입니다.
    return await sse.handle_sse(
        request.scope,
        request._receive, # Starlette 내부 receive
        request._send,    # Starlette 내부 send
        server
    )

async def health_check(request):
    """Render 배포 성공 확인용"""
    return JSONResponse({"status": "ok"})

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# ✅ Inspector 연결 필수: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
