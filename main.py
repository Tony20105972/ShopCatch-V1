import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

# 1. 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-mcp")
load_dotenv()

# 2. SSE Transport 초기화
# 클라이언트가 메시지를 보낼 기본 엔드포인트를 /messages로 설정합니다.
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """GET /mcp: SSE 연결을 수립하고 서버 메시지 루프를 실행합니다."""
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
    """POST /messages 또는 POST /mcp: 클라이언트의 JSON-RPC 메시지를 처리합니다."""
    # SseServerTransport가 내부적으로 sessionId 쿼리 파라미터를 확인하여
    # 알맞은 클라이언트 세션에 메시지를 전달합니다.
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )

async def health_check(request):
    """서비스 생존 확인용"""
    return Response("MCP Server is Running", status_code=200)

# 3. 애플리케이션 라우팅
# PlayMCP와 Inspector가 각각 /mcp 또는 /messages로 POST를 보내는 모든 상황에 대응합니다.
app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET"]),
        
        # SSE 스트림 연결 통로
        Route("/mcp", endpoint=handle_sse, methods=["GET"]),
        
        # 메시지 수신 통로 (두 경로 모두 허용하여 호환성 극대화)
        Route("/mcp", endpoint=handle_messages, methods=["POST"]),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    # Render 포트 바인딩
    port = int(os.environ.get("PORT", 10000))
    logger.info(f"🚀 MCP Server starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
