import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from mcp.server import Server
from mcp.types import JSONRPCResponse
from server import server as mcp_server # 이미 정의된 MCP 서버 객체

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server")
load_dotenv()

async def handle_mcp_request(request):
    """
    POST /mcp: Streamable HTTP 방식 처리
    세션(sessionId) 없이 JSON-RPC 요청을 직접 받아 처리합니다.
    """
    try:
        # 1. 클라이언트로부터 JSON-RPC 요청 읽기
        body = await request.json()
        logger.info(f"Received request: {body.get('method')}")

        # 2. MCP 서버 객체를 통해 직접 요청 실행 (Stateless 방식)
        # sse_transport 대신 서버의 직접 실행 로직을 사용합니다.
        # mcp_server는 이미 정의된 Server 객체여야 합니다.
        response = await mcp_server._router.handle_request(body, None)
        
        # 3. 처리 결과를 JSON으로 반환
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"Error processing MCP request: {e}")
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32603, "message": str(e)}, "id": None},
            status_code=500
        )

async def health_check(request):
    return Response("OK", status_code=200)

# 가이드라인에 따른 라우팅 설정
routes = [
    Route("/", endpoint=health_check, methods=["GET"]),
    # Streamable HTTP는 주로 POST 하나로 통신합니다.
    Route("/mcp", endpoint=handle_mcp_request, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
