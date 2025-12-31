import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

# 로깅 설정: Render 로그에서 확인 가능하도록 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")
load_dotenv()

# 1. SSE Transport 설정
# PlayMCP와 Inspector는 연결 시 서버가 알려주는 'endpoint'로 POST를 보냅니다.
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """
    GET /mcp 경로로 들어오는 SSE 연결을 처리합니다.
    """
    async with sse.connect_scope(
        request.scope, 
        request.receive, 
        request._send
    ) as (read_stream, write_stream):
        # MCP 서버를 실행하여 스트림을 브릿지합니다.
        await mcp_server.run(
            read_stream,
            write_stream,
            mcp_server.create_initialization_options()
        )

async def handle_messages(request):
    """
    POST /messages 경로로 들어오는 클라이언트의 JSON-RPC 메시지를 처리합니다.
    """
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )

async def health_check(request):
    """Render의 Health Check 및 브라우저 접속 확인용"""
    return Response("MCP Server is Running", status_code=200)

# 2. 애플리케이션 라우팅 구성
app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET"]),
        Route("/mcp", endpoint=handle_sse, methods=["GET"]),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    # Render는 PORT 환경변수를 할당하므로 이를 반드시 준수해야 합니다.
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Starting MCP server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
