import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성
sse = SseServerTransport("/messages")

# 2. 핸들러 수정 (connect_scope 사용)
async def handle_sse(request):
    """
    최신 SDK에서는 connect_scope를 사용하여 
    scope, receive, send를 MCP 서버와 연결합니다.
    """
    async with sse.connect_scope(
        request.scope, 
        request._receive, 
        request._send
    ) as (read_stream, write_stream):
        # MCP 서버를 실행하고 초기화 옵션을 전달합니다.
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

async def health_check(request):
    """Render 배포 성공 확인용"""
    return JSONResponse({"status": "ok"})

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # 클라이언트가 SSE 연결을 시작하는 엔드포인트
        Route("/sse", endpoint=handle_sse), 
        # 클라이언트가 서버로 메시지를 보내는 엔드포인트
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# Inspector 연결을 위한 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    # Render 환경의 PORT 변수 대응
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
