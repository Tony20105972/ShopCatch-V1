import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from mcp.server.sse import SseServerTransport
from server import server as mcp_server

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-main")

load_dotenv()

# 1. 트랜스포트 설정
sse_transport = SseServerTransport("/mcp")

# 2. 통합 핸들러 (라이브러리 내부 메서드 의존성 제거)
async def handle_everything(request):
    try:
        # HEAD 요청은 Render 헬스체크용으로 즉시 응답
        if request.method == "HEAD":
            from starlette.responses import Response
            return Response(status_code=200)

        if request.method == "POST":
            # POST 메시지 처리
            await sse_transport.handle_post_message(
                request.scope, request.receive, request._send
            )
        else:
            # GET 요청 시: sse_transport.connect_scope를 사용해야 합니다.
            # 이 메서드가 최신 mcp 라이브러리의 표준 연결 방식입니다.
            async with sse_transport.connect_scope(
                request.scope, request.receive, request._send
            ) as (read_stream, write_stream):
                await mcp_server.run(read_stream, write_stream, mcp_server.create_initialization_options())

    except Exception as e:
        logger.error(f"Error handling request: {str(e)}")
        from starlette.responses import JSONResponse
        return JSONResponse({"error": str(e)}, status_code=500)

# 3. 라우팅 설정
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
