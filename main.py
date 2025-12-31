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

# [핵심] Starlette의 'NoneType' 에러를 방지하기 위한 더미 응답 클래스
class DoneResponse(Response):
    async def __call__(self, scope, receive, send):
        # 이미 handle_post_message에서 응답을 보냈으므로 
        # 여기서는 아무것도 전송하지 않고 종료합니다.
        pass

async def handle_sse(request):
    """GET /mcp: SSE 연결"""
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
    """POST /messages 및 /mcp: 메시지 수신"""
    # 1. MCP SDK가 메시지를 처리하고 응답을 보내게 합니다.
    await sse.handle_post_message(
        request.scope, 
        request.receive, 
        request._send
    )
    # 2. [가장 중요] Starlette에게 '호출 가능한 응답 객체'를 리턴하여 
    # TypeError를 방지합니다.
    return DoneResponse()

async def health_check(request):
    return Response("OK", status_code=200)

routes = [
    Route("/", endpoint=health_check, methods=["GET"]),
    Route("/mcp", endpoint=handle_sse, methods=["GET"]),
    Route("/mcp", endpoint=handle_messages, methods=["POST"]),
    Route("/messages", endpoint=handle_messages, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
