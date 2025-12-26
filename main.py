import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server # 님이 작성한 server.py의 server 객체

# 1. 트랜스포트 생성
sse = SseServerTransport("/messages")

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 2. 핵심: 1.0.0 버전은 'connect_scope'를 써서 스트림을 수동으로 연결해야 함
async def handle_sse(scope, receive, send):
    # 이 구문이 1.0.0 버전의 핵심입니다.
    async with sse.connect_scope(scope, receive, send) as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # /sse로 접속하면 handle_sse가 실행되며 연결 완료
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        # 클라이언트 응답을 받기 위한 필수 경로
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
