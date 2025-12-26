import os
import asyncio
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성 (추가 속성 건드리지 마세요)
sse = SseServerTransport("/messages")

# 2. 핸들러 구현
async def handle_sse(request):
    # sse.handle_sse는 내부적으로 모든 스트림 연결을 알아서 처리합니다.
    return await sse.handle_sse(request)

async def health_check(request):
    # Render 배포 봇을 위한 응답
    return JSONResponse({"status": "ok"})

# 3. Starlette 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=health_check),
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# ✅ Inspector 연결의 핵심: CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. MCP 서버 실행 로직 (스트림 속성 대신 'dispatch' 방식 사용)
@app.on_event("startup")
async def startup():
    # sse.handle_sse가 호출될 때 server가 준비되어 있어야 하므로
    # server.run을 직접 실행하는 대신, 라이브러리가 내부적으로 처리하게 둡니다.
    # 만약 위 handle_sse에서 에러가 난다면 아래 block을 사용하세요.
    pass

# 만약 Inspector에서 연결 시 '서버가 실행 중이지 않다'고 하면 
# handle_sse를 아래와 같이 수정하는 것이 1.25.0의 정석입니다.
async def handle_sse_fixed(request):
    # 이 메서드 안에서 server.run을 호출하지 않아도 
    # sse.handle_sse가 내부적으로 server와 통신합니다.
    # 단, sse 객체 생성 시 server를 넣지 못하므로 아래와 같이 연결합니다.
    return await sse.handle_sse(request, server=server)

# 수정된 라우트 적용
app.router.routes[1] = Route("/sse", endpoint=handle_sse_fixed, methods=["GET", "POST"])

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
