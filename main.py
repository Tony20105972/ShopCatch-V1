import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport
from server import server

# 1. SSE 트랜스포트 생성
sse = SseServerTransport("/messages")

# 2. 핸들러 함수: SDK의 handle_sse를 직접 연결
async def handle_sse(request):
    # sse.handle_sse는 Starlette의 Request를 인자로 받아 처리하는 표준 메서드입니다.
    return await sse.handle_sse(request)

# 3. Starlette 앱 설정
app = Starlette(
    routes=[
        # Inspector 연결을 위해 GET, POST 모두 허용
        Route("/sse", endpoint=handle_sse, methods=["GET", "POST"]),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

# ✅ Inspector(브라우저) 연결을 위한 필수 CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 서버 기동 시 MCP 엔진과 트랜스포트 결합
@app.on_event("startup")
async def startup():
    # 백그라운드에서 MCP 서버를 구동하여 SSE 스트림과 연결
    import asyncio
    asyncio.create_task(server.run(
        sse.read_stream,
        sse.write_stream,
        server.create_initialization_options()
    ))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
