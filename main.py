import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. 트랜스포트 설정
# PlayMCP는 /sse로 접속해 세션을 만들고, /messages로 데이터를 보냅니다.
sse = SseServerTransport("/messages")

# 2. 통합 ASGI 앱 (Streamable 대응)
async def app(scope, receive, send):
    # (1) GET /sse : PlayMCP가 초기 세션을 맺을 때
    if scope["type"] == "http" and scope["path"] == "/sse" and scope["method"] == "GET":
        async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )

    # (2) POST /messages : PlayMCP가 툴 호출(Streamable 메시지)을 보낼 때
    elif scope["type"] == "http" and scope["path"].startswith("/messages") and scope["method"] == "POST":
        await sse.handle_post_message(scope, receive, send)

    # (3) Root / Health Check : Render 배포 상태 확인용
    else:
        response = JSONResponse({
            "status": "ok", 
            "transport": "streamable/sse",
            "info": "ShopCatch MCP Server is live"
        })
        await response(scope, receive, send)

# 3. CORS 설정 (PlayMCP 연결의 핵심)
# 인증 정보(credentials)와 노출 헤더를 명확히 선언합니다.
final_app = CORSMiddleware(
    app, 
    allow_origins=["*"], 
    allow_methods=["GET", "POST", "OPTIONS"], 
    allow_headers=["*"],
    allow_credentials=True, 
    expose_headers=["X-Session-Id", "Content-Type"]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Render 환경에서 안정적인 연결 유지를 위해 설정 추가
    uvicorn.run(
        final_app, 
        host="0.0.0.0", 
        port=port, 
        proxy_headers=True,
        forwarded_allow_ips="*",
        timeout_keep_alive=65
    )
