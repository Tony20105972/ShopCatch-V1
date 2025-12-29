import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from mcp.server.sse import SseServerTransport

# server.py에서 업그레이드한 고성능 서버 객체 가져오기
from server import server as mcp_server

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-main")

load_dotenv()

# 1. 트랜스포트 설정 (Streamable HTTP용)
# 내부 경로는 /mcp로 지정하지만, handle_everything에서 모든 경로를 수용함
sse_transport = SseServerTransport("/mcp")

# 2. 통합 핸들러 (어떤 경로, 어떤 방식이든 다 받아줌)
async def handle_everything(request):
    """
    Inspector나 클라이언트가 어떤 엔드포인트를 찔러도 
    MCP 서버로 연결해주는 만능 게이트웨이
    """
    try:
        if request.method == "POST":
            # JSON-RPC 메시지 처리 (POST)
            await sse_transport.handle_post_message(request.scope, request.receive, request.send)
        else:
            # SSE 연결 수립 (GET)
            async with sse_transport.connect_scope(request.scope, request.receive, request.send) as scope:
                # server.py의 고성능 로직 실행
                await mcp_server.run(scope[0], scope[1], sse_transport.handle_sse)
    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        from starlette.responses import JSONResponse
        return JSONResponse({"error": "Internal Server Error", "details": str(e)}, status_code=500)

# 3. 모든 루트를 handle_everything으로 라우팅 (404/405 방지)
app = Starlette(
    routes=[
        Route("/", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/sse", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/mcp", endpoint=handle_everything, methods=["GET", "POST"]),
    ]
)

# 4. 서버 실행
if __name__ == "__main__":
    # Render 환경의 PORT 변수 우선 사용
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
