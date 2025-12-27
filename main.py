import os
import uvicorn
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
        # connect_sse는 컨텍스트 매니저로 작동하며 연결을 유지합니다.
        async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options()
            )
    
    # (2) /messages 경로 처리 (POST 요청)
    # scope["path"]가 /messages로 시작하는 모든 요청을 sse 핸들러로 넘깁니다.
    elif scope["type"] == "http" and scope["path"].startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)
    
    # (3) 기본 Health Check (Render 배포용)
    else:
        response = JSONResponse({"status": "ok"})
        await response(scope, receive, send)

# 3. CORS 미들웨어 입히기
final_app = CORSMiddleware(
    app, 
    allow_origins=["*"], 
    allow_methods=["*"], 
    allow_headers=["*"],
    expose_headers=["*"] # Inspector가 세션 ID를 읽기 위해 필수
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Render 타임아웃 방지를 위해 keep-alive 설정 추가
    uvicorn.run(
        final_app, 
        host="0.0.0.0", 
        port=port, 
        access_log=True,
        timeout_keep_alive=65
    )
