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

# 2. 통합 핸들러 (ASGI 연결 인터페이스 직접 추출)
async def handle_everything(request):
    try:
        # Starlette Request에서 ASGI의 기본 통신 인터페이스를 직접 가져옵니다.
        # 이것이 'Request object has no attribute send' 에러를 막는 핵심입니다.
        scope = request.scope
        receive = request.receive
        send = scope.get("ask") or request._send # Starlette의 내부 send 인터페이스 활용

        if request.method == "POST":
            # HTTP POST 메시지 처리
            await sse_transport.handle_post_message(scope, receive, request._send)
        else:
            # GET 요청 시 SSE 연결 및 MCP 서버 실행
            # mcp_server.run은 이 인터페이스들을 통해 클라이언트와 대화합니다.
            await mcp_server.run(
                receive,
                request._send,
                sse_transport.handle_sse
            )
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        from starlette.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)

# 3. 모든 루트 통합
app = Starlette(
    routes=[
        Route("/", endpoint=handle_everything, methods=["GET", "POST", "HEAD"]),
        Route("/sse", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/mcp", endpoint=handle_everything, methods=["GET", "POST"]),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
