import os
import logging
import uvicorn
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse, Response
from server import server as mcp_server  # 작성하신 server.py의 server 객체

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-stateless-server")
load_dotenv()

async def handle_mcp_request(request):
    """
    POST /mcp: 가이드라인의 'Streamable HTTP' 및 'Stateless'를 충족하는 핸들러
    """
    try:
        # 1. 요청 바디(JSON-RPC 2.0) 추출
        body = await request.json()
        logger.info(f"📥 요청 수신: {body.get('method')}")

        # 2. [핵심] 세션 없이 서버 라우터를 직접 호출
        # SseServerTransport를 쓰지 않고 서버 객체의 내부 메서드를 사용하여 즉시 결과를 얻습니다.
        # 가이드라인의 'no session' 조건을 완벽히 충족합니다.
        response = await mcp_server._router.handle_request(body, None)
        
        # 3. JSON-RPC 규격에 맞게 즉시 반환
        return JSONResponse(response)
        
    except Exception as e:
        logger.error(f"❌ 처리 중 에러 발생: {e}")
        return JSONResponse(
            {
                "jsonrpc": "2.0", 
                "error": {"code": -32603, "message": str(e)}, 
                "id": body.get("id") if 'body' in locals() else None
            },
            status_code=500
        )

async def health_check(request):
    """Render 활성 확인용"""
    return Response("OK", status_code=200)

# 라우팅 설정
routes = [
    Route("/", endpoint=health_check, methods=["GET"]),
    # 플랫폼과 Inspector가 찌르는 단일 진입점
    Route("/mcp", endpoint=handle_mcp_request, methods=["POST"]),
]

app = Starlette(debug=True, routes=routes)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # 외부 접속 허용을 위해 0.0.0.0 바인딩
    uvicorn.run(app, host="0.0.0.0", port=port)
