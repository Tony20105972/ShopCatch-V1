import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
# 1.25.0 버전의 표준인 StreamableHttpServerTransport를 사용합니다.
from mcp.server.streamable_http import StreamableHttpServerTransport
from server import server # 님이 작성한 server.py의 server 객체

# 1. 트랜스포트 생성 (가장 깔끔한 최신 방식)
transport = StreamableHttpServerTransport()

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 2. 통합 핸들러 (인스펙터의 모든 요청을 여기서 처리)
async def handle_mcp(request):
    """
    인스펙터가 GET으로 오든 POST로 오든 이 함수가 
    모든 스트림 연결(Streamable HTTP)을 자동으로 처리합니다.
    """
    return await transport.handle_request(
        request.scope,
        request.receive,
        request.send,
        server
    )

# 3. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # 인스펙터가 /sse로 요청을 보내므로 경로를 /sse로 유지합니다.
        Route("/sse", endpoint=handle_mcp, methods=["GET", "POST"]),
    ]
)

# CORS 설정 (이게 있어야 인스펙터 웹 UI에서 에러가 안 납니다)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    # Render의 포트 환경변수를 따라갑니다.
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
