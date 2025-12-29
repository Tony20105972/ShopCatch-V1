import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. 트랜스포트 설정
sse = SseServerTransport("/messages")

async def app(scope, receive, send):
    path = scope.get("path", "")
    method = scope.get("method", "")

    # (1) /sse 경로: PlayMCP의 메인 통로
    if path == "/sse":
        if method == "GET":
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        elif method == "POST":
            # 세션 ID가 없는 POST 요청이 들어오면 에러 대신 '빈 성공' JSON을 보냄
            query_params = scope.get("query_string", b"").decode()
            if "session_id" not in query_params:
                # PlayMCP가 기대하는 최소한의 JSON 구조
                response = JSONResponse({}, status_code=200)
                await response(scope, receive, send)
            else:
                await sse.handle_post_message(scope, receive, send)

    # (2) /messages 경로: 데이터 전송 통로
    elif path.startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)

    # (3) 그 외 모든 경로: 무조건 JSON으로 대답 (Content-Type 에러 방지)
    else:
        response = JSONResponse({"status": "ok"}, status_code=200)
        await response(scope, receive, send)

# 3. CORS 설정 (반드시 모든 헤더 허용)
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
