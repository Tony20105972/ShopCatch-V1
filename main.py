import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

# 임포트 에러를 방지하기 위해 최상위 레벨에서 가져옵니다.
from mcp.server.streamable_http import StreamableHttpTransport
from server import server

# 1. 트랜스포트 초기화 (이름 확인: StreamableHttpTransport)
transport = StreamableHttpTransport()

async def health_check(request):
    return JSONResponse({"status": "ok"})

# 2. 핸들러 정의
async def handle_mcp(request):
    # 최신 버전에서는 handle_request 메서드가 모든 연결을 처리합니다.
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
        # 인스펙터가 접속할 경로
        Route("/sse", endpoint=handle_mcp, methods=["GET", "POST"]),
    ]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
