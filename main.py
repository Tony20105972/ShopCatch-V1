import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount, BaseRoute
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

# 2. 에러 해결의 핵심: ASGI 직접 처리 클래스
class MCPRoute(BaseRoute):
    """
    Starlette의 복잡한 로직을 건너뛰고 
    Uvicorn이 주는 (scope, receive, send)를 그대로 MCP에 꽂아줍니다.
    """
    async def handle(self, scope, receive, send):
        if scope["type"] == "http" and scope["path"] == "/sse":
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # 일반 Route 대신 우리가 만든 MCPRoute를 직접 넣습니다.
        MCPRoute(), 
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
