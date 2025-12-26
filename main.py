import os
import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

# 2. 핸들러 구현 (v1.25.0 공식 메서드 connect_sse 사용)
async def handle_sse(request):
    """
    mcp-python SDK 1.x 버전에서는 handle_sse 대신 
    connect_sse(scope, receive, send, server)를 사용합니다.
    """
    return await sse.connect_sse(
        request.scope, 
        request.receive, 
        request.send, 
        server
    )

async def health_check(request):
    """Render 배포 성공을 위한 루트 응답"""
    return JSONResponse({"status": "ok"})

# 3. Starlette 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# ✅ Inspector 연결 필수: CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Render 환경 바인딩
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True)
