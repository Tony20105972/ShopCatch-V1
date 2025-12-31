import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")
load_dotenv()

# SSE Transport 초기화
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """GET /mcp: SSE 스트림 연결"""
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
    """POST /messages 및 POST /mcp 처리"""
    # 1. SDK 핸들러 실행 (내부적으로 메시지 처리)
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )
    # 2. 중요: Starlette 에러 방지를 위해 명시적으로 빈 Response 반환
    return Response(status_code=202)

async def health_check(request):
    return Response("OK", status_code=200)

app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET"]),
        # GET /mcp (SSE 연결)
        Route("/mcp", endpoint=handle_sse, methods=["GET"]),
        # POST /mcp (Inspector 대응)
        Route("/mcp", endpoint=handle_messages, methods=["POST"]),
        # POST /messages (표준 대응)
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
