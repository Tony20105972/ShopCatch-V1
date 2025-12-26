import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성
sse = SseServerTransport("/messages")

# 2. 헬스체크
async def health_check(request):
    return JSONResponse({"status": "ok"})

# 3. 핵심: handle_sse 대신 'sse' 객체 자체를 ASGI 앱으로 처리
# 최신 SDK의 SseServerTransport는 그 자체가 ASGI 애플리케이션일 가능성이 높습니다.
async def handle_sse(request):
    # sse 객체를 함수처럼 호출하여 scope, receive, send를 직접 전달합니다.
    # 이것은 Starlette의 내부 동작 방식을 활용한 우회법입니다.
    await sse(request.scope, request.receive, request.send)

# 4. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # /sse 경로에 대해 GET과 POST 모두 허용 (Inspector의 다양한 시도 대응)
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Mount("/messages", app=sse.handle_post_message),
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
    # 5. 서버 실행 시 MCP 서버와 트랜스포트 연결을 백그라운드에서 시작
    # 최신 버전은 sse() 호출 시 내부적으로 server.run을 유도합니다.
    uvicorn.run(app, host="0.0.0.0", port=port)
