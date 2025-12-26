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

# 2. 핸들러: handle_sse 대신 connect_sse를 사용합니다.
async def handle_sse(request):
    """
    1.25.0 버전에서는 connect_sse 메서드를 통해 
    scope, receive, send를 server와 연결합니다.
    """
    async with sse.connect_sse(
        request.scope, 
        request.receive, 
        request.send
    ) as (read_stream, write_stream):
        # 서버와 스트림을 연결하여 실행합니다.
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
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
