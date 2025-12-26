import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from mcp.server import Server
from server import server  # server.py에서 정의한 server 객체

# 1. SSE 트랜스포트 생성
sse = SseServerTransport("/messages")

# 2. 핸들러 함수 직접 구현 (가장 확실한 방법)
async def handle_sse(request):
    """SDK v1.2.0+ 기준 SSE 연결 핸들러"""
    async with sse.connect_scope(
        request.scope, 
        request.receive, 
        request.send
    ) as (read_stream, write_stream):
        # 서버와 스트림을 직접 연결하여 실행
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# 3. Starlette 앱 설정
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse), # 직접 만든 핸들러 연결
        Mount("/messages", app=sse.handle_post_message),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 ShopCatch V1 Final Live: 0.0.0.0:{port}/sse")
    uvicorn.run(app, host="0.0.0.0", port=port)
