import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from server import server  # 위에서 만든 server 객체 임포트

# SSE 트랜스포트 설정 (메시지 전송 경로 지정)
sse = SseServerTransport("/messages")

async def handle_sse(request):
    """SSE 연결 엔드포인트"""
    async with sse.connect_scope(request.scope, request.receive, request.send):
        await server.run(
            sse.read_socket,
            sse.write_socket,
            server.create_initialization_options()
        )

# Starlette 앱 정의
app = Starlette(
    routes=[
        Route("/sse", endpoint=handle_sse),  # 카카오 Play MCP가 연결할 주소
        Mount("/messages", app=sse.handle_post_message), # 메시지 통로
    ]
)

if __name__ == "__main__":
    # Render의 PORT 환경 변수를 읽어 0.0.0.0으로 바인딩
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 ShopCatch V1 Live at: http://0.0.0.0:{port}/sse")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
