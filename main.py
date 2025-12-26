import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 설정
sse = SseServerTransport("/messages")

# 2. 핸들러 구현 (가장 안전한 방어적 코드)
async def handle_sse(request):
    # sse.handle_sse가 있으면 그것을 사용 (최신 SDK 표준)
    if hasattr(sse, "handle_sse"):
        return await sse.handle_sse(request)
    
    # 만약 없다면, 수동으로 scope 연결 (구버전 대응)
    # 1.25.0 이상에서는 보통 sse.scope 또는 sse.handle_sse를 기대합니다.
    async with sse.scope(request.scope, request.receive, request.send) as (read, write):
        await server.run(read, write, server.create_initialization_options())

# 3. Starlette 앱 설정
app = Starlette(
    routes=[
        # GET/POST 모두 허용 (Inspector 및 카카오 대응)
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# ✅ Inspector 테스트를 위한 CORS 설정 (이게 없으면 Inspector가 거부함)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 ShopCatch V1 Standard Live: http://0.0.0.0:{port}/sse")
    uvicorn.run(app, host="0.0.0.0", port=port)
