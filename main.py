import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")
load_dotenv()

sse = SseServerTransport("/messages")

async def handle_sse(request):
    """GET /mcp: SSE 연결용 (정상)"""
    async with sse.connect_scope(
        request.scope, 
        request.receive, 
        request._send
    ) as (read_stream, write_stream):
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

async def handle_messages(request):
    """POST /messages & /mcp: 메시지 수신용"""
    # [체크 1] sse.handle_post_message가 직접 응답(send)을 처리합니다.
    # [체크 2] 따라서 이 함수는 절대 아무것도 return 하면 안 됩니다 (None 유지).
    # [체크 3] Starlette의 RuntimeError를 방지하기 위해 여기서 함수를 종료합니다.
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )

async def health_check(request):
    return Response("OK", status_code=200)

# 라우팅 테이블
routes = [
    Route("/", endpoint=health_check, methods=["GET"]),
    Route("/mcp", endpoint=handle_sse, methods=["GET"]),
    # POST 엔드포인트에서 'return'을 제거한 handle_messages를 연결
    Route("/mcp", endpoint=handle_messages, methods=["POST"]),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
