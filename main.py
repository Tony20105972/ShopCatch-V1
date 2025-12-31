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
    """GET /mcp: SSE 스트림 연결 포트"""
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
    try:
        # 세션 ID가 없는 요청이 들어오면 SDK 내부에서 에러를 발생시키거나 
        # 직접 응답을 보내버립니다.
        await sse.handle_post_message(
            request.scope, 
            request.receive, 
            request._send
        )
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        # 이미 응답이 나갔을 수도 있으므로, 예외 상황에서만 응답을 시도합니다.
        # 하지만 Starlette 라우터는 항상 무언가를 반환해야 하므로
        # 아래와 같이 반환값을 비워두거나 명시하지 않는 구조로 처리합니다.
        pass

async def health_check(request):
    return Response("OK", status_code=200)

# Starlette의 가이드에 따라 함수 기반이 아닌 
# 명시적으로 Response를 반환하지 않아도 되는 미들웨어적 처리를 위해 수정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check, methods=["GET"]),
        Route("/mcp", endpoint=handle_sse, methods=["GET"]),
        # POST 요청들은 Response 객체를 직접 return 하지 않고 SDK에 맡깁니다.
        Route("/mcp", endpoint=handle_messages, methods=["POST"]),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
