import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from mcp.server.sse import SseServerTransport

# server.py에서 고성능 서버 객체 가져오기
from server import server as mcp_server

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-main")

load_dotenv()

# 1. 트랜스포트 설정 (Streamable HTTP 기반)
sse_transport = SseServerTransport("/mcp")

# 2. 통합 핸들러 (오류 원인이었던 connect_scope 제거 및 구조 최적화)
async def handle_everything(request):
    try:
        if request.method == "POST":
            # HTTP POST를 통한 메시지 전달
            await sse_transport.handle_post_message(request.scope, request.receive, request.send)
        else:
            # SSE 전송 방식을 이용한 연결 수립 (GET)
            # mcp.server.run은 내부적으로 transport의 기능을 호출함
            await mcp_server.run(
                request.receive,
                request.send,
                sse_transport.handle_sse
            )
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        from starlette.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)

# 3. 모든 루트 통합 (404, 405 방지)
app = Starlette(
    routes=[
        Route("/", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/sse", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/mcp", endpoint=handle_everything, methods=["GET", "POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
