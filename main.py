import os
import logging
import uvicorn
import anyio
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import StreamingResponse, Response
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-main")
load_dotenv()

# Transport 초기화 (PlayMCP 요구사항에 맞춰 /messages 경로 설정)
sse_transport = SseServerTransport("/messages")

async def handle_stream(request):
    """
    HTTP 스트리밍 응답을 통해 MCP 데이터를 전송 (Streamable Transport)
    """
    async def event_generator():
        # mcp-python-sdk의 connect_scope를 사용하여 스트림 브릿지 생성
        async with sse_transport.connect_scope(
            request.scope, 
            request.receive, 
            request._send
        ) as (read_stream, write_stream):
            # 서버 실행
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )

    # Content-Type을 text/event-stream 또는 application/octet-stream으로 설정
    # PlayMCP의 요구사항에 따라 적절한 타입이 필요할 수 있습니다.
    return StreamingResponse(
        event_generator(), 
        media_type="text/event-stream" 
    )

async def handle_post(request):
    """POST 요청 처리 (JSON-RPC)"""
    await sse_transport.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )

async def health_check(request):
    return Response("OK", status_code=200)

app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET", "HEAD"]),
        Route("/mcp", endpoint=handle_stream, methods=["GET"]),
        Route("/messages", endpoint=handle_post, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
