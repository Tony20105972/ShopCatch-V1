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

# 3. 핵심: Starlette의 추상화를 한 단계 건너뛰고 ASGI 인터페이스로 직접 대응
# 이렇게 하면 'AttributeError: Request object has no attribute send'를 완벽히 피합니다.
async def handle_sse(scope, receive, send):
    # sse.handle_sse가 있든 없든, sse 객체 자체가 ASGI 앱 역할을 수행하도록 호출
    # 버전 1.25.0 내외의 대부분의 MCP SDK는 이 호출 방식을 지원합니다.
    if hasattr(sse, "handle_sse"):
        await sse.handle_sse(scope, receive, send)
    else:
        # handle_sse 메서드가 없는 경우 객체 자체를 실행
        await sse(scope, receive, send)

# 4. 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        # Route의 endpoint에 handle_sse를 직접 넣으면 
        # Starlette는 자동으로 (scope, receive, send)를 인자로 넘겨줍니다.
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
    uvicorn.run(app, host="0.0.0.0", port=port)
