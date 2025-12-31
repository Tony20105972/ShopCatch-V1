import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from server import server as mcp_server # 작성하신 server.py의 server 객체

# 1. 환경 설정 및 로깅
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-stateless-server")

async def handle_mcp_request(request):
    """
    POST /mcp: 가이드라인의 'Streamable HTTP' 전용 핸들러.
    세션 관리(SseServerTransport)를 완전히 배제하고 직접 처리합니다.
    """
    try:
        # 클라이언트의 JSON-RPC 요청 읽기
        body = await request.json()
        logger.info(f"📥 요청 수신: {body.get('method')}")

        # [핵심] SseServerTransport를 거치지 않고 서버 내부 라우터로 직접 전달
        # 가이드라인의 'Stateless' 및 'No Session'을 완벽히 만족합니다.
        # handle_request의 두 번째 인자인 Context는 Stateless이므로 None을 줍니다.
        response = await mcp_server._router.handle_request(body, None)
        
        # 즉시 JSON 응답 반환
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"❌ 처리 에러: {e}")
        return JSONResponse(
            {
                "jsonrpc": "2.0", 
                "error": {"code": -32603, "message": str(e)}, 
                "id": body.get("id") if 'body' in locals() else None
            },
            status_code=500
        )

async def health_check(request):
    return Response("OK", status_code=200)

# 2. 가이드라인 준수 라우팅
# 더 이상 GET /mcp (세션 수립) 과정이 필요 없습니다.
routes = [
    Route("/", endpoint=health_check, methods=["GET"]),
    Route("/mcp", endpoint=handle_mcp_request, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
