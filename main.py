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

# 2. 통합 핸들러
async def handle_everything(request):
    try:
        if request.method == "POST":
            # HTTP POST 메시지 처리
            await sse_transport.handle_post_message(
                request.scope, 
                request.receive, 
                request._send
            )
        elif request.method == "GET":
            # 최신 버전 mcp 라이브러리 인터페이스: create_sse_handler 사용
            sse_handler = await sse_transport.create_sse_handler(
                request.scope, 
                request.receive, 
                request._send
            )
            # mcp_server.run에 핸들러와 통신 로직 연결
            await mcp_server.run(
                request.receive,
                request._send,
                sse_handler
            )
        elif request.method == "HEAD":
            # 헬스체크용 (Render용)
            from starlette.responses import Response
            return Response(status_code=200)

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
