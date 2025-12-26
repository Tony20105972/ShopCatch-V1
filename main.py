import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 2. 핵심 수정: Starlette Request를 거치지 않고 ASGI raw 함수로 처리
async def handle_sse(scope, receive, send):
    """
    Starlette이 request 객체를 만들어서 넘겨주기 전 단계(scope, receive, send)에서
    직접 connect_sse를 호출해야 에러가 나지 않습니다.
    """
    async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # endpoint에 handle_sse 함수 자체를 넘겨 ASGI 방식으로 동작하게 합니다.
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
