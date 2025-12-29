import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. 트랜스포트 설정 (메시지 전송 경로를 /messages로 설정)
sse = SseServerTransport("/messages")

async def app(scope, receive, send):
    path = scope.get("path", "")
    method = scope.get("method", "")

    # (1) /sse 경로 처리
    if path == "/sse":
        # GET 요청일 때 세션 생성 (표준 방식)
        if method == "GET":
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        # POST 요청일 때: 세션 ID가 없으면 에러 대신 핸들러로 유도
        elif method == "POST":
            try:
                await sse.handle_post_message(scope, receive, send)
            except Exception as e:
                # 세션 ID가 없는 초기 POST 요청일 경우를 대비해 200 응답만 보냄
                response = JSONResponse({"status": "retry_with_get", "detail": str(e)}, status_code=200)
                await response(scope, receive, send)

    # (2) /messages 경로 처리 (MCP 표준 메시지 통로)
    elif path.startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)

    # (3) 기본 헬스체크 (Render 유지용)
    else:
        response = JSONResponse({"status": "live", "mcp": "ready"})
        await response(scope, receive, send)

# 3. CORS 설정 (PlayMCP 프록시 통과 필수)
final_app = CORSMiddleware(
    app,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    allow_credentials=True
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(final_app, host="0.0.0.0", port=port, timeout_keep_alive=65)
