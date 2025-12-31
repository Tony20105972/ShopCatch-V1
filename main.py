import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import Response
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

# 1. 로깅 및 환경 설정 (체크 완료)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")
load_dotenv()

# 2. SSE Transport 설정 (메시지 수신 경로 체크 완료)
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """GET /mcp: SSE 스트림을 생성하고 MCP 서버 루프를 실행합니다."""
    # connect_scope는 응답을 직접 처리하므로 return이 필요 없습니다.
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
    """POST /messages & POST /mcp: JSON-RPC 메시지 처리"""
    # [트리플 체크]: sse.handle_post_message는 내부적으로 응답을 보내지만 
    # Starlette 라우터의 'NoneType' 에러를 막기 위해 반드시 Response 객체를 명시적으로 리턴해야 합니다.
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )
    # 빈 Response 객체를 반환하여 Starlette의 응답 사이클을 명확히 끝냅니다.
    return Response(content="", status_code=202)

async def health_check(request):
    """Render 생존 확인용"""
    return Response("OK", status_code=200)

# 3. 라우팅 테이블 (중복 경로 및 메서드 체크 완료)
routes = [
    Route("/", endpoint=health_check, methods=["GET"]),
    # SSE 연결
    Route("/mcp", endpoint=handle_sse, methods=["GET"]),
    # 메시지 전송 (Inspector는 /mcp로, PlayMCP는 /messages로 보낼 수 있음)
    Route("/mcp", endpoint=handle_messages, methods=["POST"]),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    # Render 포트 바인딩 체크 완료
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
