import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성
# /messages는 클라이언트가 서버로 데이터를 보낼 때 사용하는 경로입니다.
sse = SseServerTransport("/messages")

async def health_check(request):
    """Render 배포 헬스체크 및 서버 상태 확인"""
    return JSONResponse({"status": "ok", "mcp_server": "running"})

# 2. 통합 핸들러
# Starlette의 주입 방식과 MCP의 기대 방식 차이를 해결하는 가장 안전한 함수입니다.
async def handle_sse(request):
    # sse.handle_sse는 (scope, receive, send)를 인자로 받는 ASGI 애플리케이션 역할을 합니다.
    # 이를 직접 호출하여 Starlette 요청을 MCP 트랜스포트로 넘겨줍니다.
    return await sse.handle_sse(request.scope, request.receive, request.send)

# 3. 앱 설정
app = Starlette(
    routes=[
        # 헬스체크 (Render용)
        Route("/", endpoint=health_check),
        
        # SSE 연결 엔드포인트 (Inspector가 처음 접속하는 곳)
        Route("/sse", endpoint=handle_sse),
        
        # 메시지 수신 엔드포인트 (Inspector가 메시지를 쏘는 곳)
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# 4. CORS 설정 (Inspector 연결에 필수)
# 이게 없으면 브라우저 기반 Inspector에서 접속 거부가 발생합니다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. 서버 실행 시 MCP 서버 초기화 연동
@app.on_event("startup")
async def startup():
    # 여기서 server는 server.py에서 가져온 mcp.server.models.Server 객체입니다.
    # SSE 트랜스포트와 서버를 연결합니다.
    # 주의: 최신 SDK 버전의 동작 방식에 따라 sse.handle_sse 내부에서 
    # 자동으로 처리되기도 하지만, 명시적 관리가 필요한 경우 여기에 로직이 추가됩니다.
    pass

if __name__ == "__main__":
    # Render는 PORT 환경변수를 사용합니다.
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
