import os
import uvicorn
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

# 2. 가장 원시적인 ASGI 앱 핸들러
async def app(scope, receive, send):
    # (1) /sse 경로로 들어오는 요청 처리
    if scope["type"] == "http" and scope["path"] == "/sse":
        async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    # (2) /messages 경로 처리 (POST 요청)
    elif scope["path"].startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)
    
    # (3) 기본 Health Check (루트 경로 등)
    else:
        response = JSONResponse({"status": "ok"})
        await response(scope, receive, send)

# 3. CORS 미들웨어 입히기
# Starlette 앱 객체로 감싸서 CORS 기능만 씁니다.
final_app = CORSMiddleware(app, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(final_app, host="0.0.0.0", port=port)
