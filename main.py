import os
import uvicorn
import asyncio
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server # 작성하신 MCP 서버 객체

# 1. SSE 트랜스포트 생성
sse = SseServerTransport("/messages")

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 2. 핵심 핸들러: 메서드 호출 대신 '스트림'을 직접 연결
async def handle_sse(scope, receive, send):
    # sse.connect_scope를 통해 읽기/쓰기 스트림을 직접 뽑아냅니다.
    # AttributeError를 피하기 위해 내부 구조를 직접 타격합니다.
    async with sse.connect_scope(scope, receive, send) as (read_stream, write_stream):
        # 뽑아낸 스트림을 MCP 서버의 run 메서드에 강제로 꽂아넣습니다.
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # 핸들러 인자가 (scope, receive, send)이므로 Starlette이 ASGI로 인식합니다.
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
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
