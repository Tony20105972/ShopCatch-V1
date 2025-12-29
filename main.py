import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

async def app(scope, receive, send):
    path = scope.get("path", "")
    method = scope.get("method", "")

    # (1) PlayMCP 연결 경로: 어떤 경우에도 일반 JSON을 리턴하지 않음
    if path == "/sse":
        if method == "GET":
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        elif method == "POST":
            # 세션 ID가 없으면 그냥 빈 응답(204)을 보내서 프록시가 에러로 인식하지 않게 함
            query_params = scope.get("query_string", b"").decode()
            if "session_id" not in query_params:
                response = Response(status_code=204) # No Content
                await response(scope, receive, send)
            else:
                await sse.handle_post_message(scope, receive, send)

    # (2) 메시지 처리 경로
    elif path.startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)

    # (3) 그 외 경로 (Render 헬스체크용): PlayMCP가 건드리지 않는 경로
    else:
        # 루트(/) 경로에서만 최소한의 응답
        if path == "/":
            response = Response("ok", media_type="text/plain")
            await response(scope, receive, send)
        else:
            response = Response(status_code=404)
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
