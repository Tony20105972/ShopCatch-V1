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

# 1. 트랜스포트 설정
sse_transport = SseServerTransport("/mcp")

# 2. 통합 핸들러 (Starlette request의 scope, receive, send를 정확히 추출)
async def handle_everything(request):
    try:
        # Starlette 핸들러에서 필요한 인자들을 추출합니다.
        scope = request.scope
        receive = request.receive
        send = request.send

        if request.method == "POST":
            # HTTP POST를 통한 메시지 전달
            await sse_transport.handle_post_message(scope, receive, send)
        else:
            # GET 요청 시 SSE 연결 수립 및 MCP 서버 실행
            await mcp_server.run(
                receive,
                send,
                sse_transport.handle_sse
            )
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        from starlette.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)

# 3. 모든 루트 통합
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
