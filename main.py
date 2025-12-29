import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

# 2. 통합 ASGI 핸들러
async def app(scope, receive, send):
    path = scope.get("path", "")
    method = scope.get("method", "")

    # (1) /sse 경로 처리
    if path == "/sse":
        if method == "GET":
            # 정상적인 초기 연결 (여기서 세션 ID가 생성됨)
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        elif method == "POST":
            # 세션 ID 없이 POST가 오면 400 에러 대신 안전하게 응답
            query_params = scope.get("query_string", b"").decode()
            if "session_id" not in query_params:
                # PlayMCP가 세션 ID를 찾을 수 있도록 유도
                return await JSONResponse(
                    {"error": "session_id_required", "message": "Please connect via GET /sse first"},
                    status_code=200 # 400 대신 200을 줘서 프록시가 죽지 않게 함
                )(scope, receive, send)
            
            await sse.handle_post_message(scope, receive, send)

    # (2) /messages 경로 처리
    elif path.startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)

    # (3) 헬스체크 및 기본 응답
    else:
        response = JSONResponse({"status": "running"})
        await response(scope, receive, send)

# 3. CORS 및 미들웨어 설정 (필수)
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
