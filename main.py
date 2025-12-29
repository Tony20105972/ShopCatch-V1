import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. 트랜스포트 설정
# 내부적으로 /messages 경로를 메시지 전송용으로 사용합니다.
sse = SseServerTransport("/messages")

async def app(scope, receive, send):
    path = scope.get("path", "")
    method = scope.get("method", "")

    # (1) 핵심: /sse 경로는 '오직' MCP 통신에만 집중
    if path == "/sse":
        if method == "GET":
            # 여기서 JSONResponse를 뱉으면 ZodError가 납니다.
            # 곧장 connect_sse로 들어가서 MCP 초기화 데이터를 보내야 합니다.
            async with sse.connect_sse(scope, receive, send) as (read_stream, write_stream):
                await server.run(
                    read_stream,
                    write_stream,
                    server.create_initialization_options()
                )
        elif method == "POST":
            # Streamable-HTTP 규격상 POST 요청도 /sse로 올 수 있습니다.
            await sse.handle_post_message(scope, receive, send)

    # (2) /messages: 추가적인 데이터 전송 경로
    elif path.startswith("/messages"):
        await sse.handle_post_message(scope, receive, send)

    # (3) 그 외 (Render 헬스체크용): /sse가 아닌 다른 곳에서만 응답
    else:
        response = JSONResponse({"mcp_server": "active"})
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
