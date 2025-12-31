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
logger = logging.getLogger("shopcatch-main")
load_dotenv()

# SSE Transport 초기화
# /messages는 표준 SSE에서 사용하는 메시지 수신 경로입니다.
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """
    GET /mcp: SSE 연결을 생성합니다.
    """
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
    """
    POST /messages 및 POST /mcp: 
    클라이언트(Inspector 등)가 보내는 JSON-RPC 메시지를 처리합니다.
    """
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )

async def health_check(request):
    """Render 헬스체크용"""
    return Response("OK", status_code=200)

# 핵심: 라우팅 설정
app = Starlette(
    routes=[
        # 1. 기본적인 접속 확인
        Route("/", endpoint=health_check, methods=["GET"]),
        
        # 2. SSE 연결 통로 (GET)
        Route("/mcp", endpoint=handle_sse, methods=["GET"]),
        
        # 3. 중요: MCP Inspector는 /mcp 경로로 직접 POST를 날립니다.
        # 이 부분이 없으면 405 Method Not Allowed가 발생합니다.
        Route("/mcp", endpoint=handle_messages, methods=["POST"]),
        
        # 4. 일반적인 SSE 메시지 수신 경로 (POST)
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    # Render 환경의 PORT 대응
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
