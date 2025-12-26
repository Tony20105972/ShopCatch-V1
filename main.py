import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
# 최신 버전에서도 가장 안정적인 SSE 트랜스포트 경로입니다.
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성
# 이 객체가 내부적으로 Streamable HTTP 메시지도 다 처리합니다.
sse = SseServerTransport("/messages")

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 2. 핸들러 (인스펙터와 통신하는 핵심)
async def handle_sse(request):
    # sse.handle_sse는 (scope, receive, send) 세 개를 정확히 인자로 받습니다.
    return await sse.handle_sse(
        request.scope, 
        request.receive, 
        request.send
    )

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # 인스펙터가 접근하는 /sse 경로
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        # 메시지 전송을 위한 /messages 경로 (SseServerTransport의 필수 설정)
        Mount("/messages", app=sse.handle_post_message),
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
