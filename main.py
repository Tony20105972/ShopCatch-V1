import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from server import server 

# 1. SSE 트랜스포트 설정
# 여기서 /messages는 클라이언트가 메시지를 보낼(POST) 경로입니다.
sse = SseServerTransport("/messages")

# 2. Starlette 앱 정의
app = Starlette(
    routes=[
        # ✅ 최신 버전 방식: sse.handle_sse를 직접 엔드포인트로 연결합니다.
        # 내부적으로 GET/POST 처리를 SDK가 알아서 합니다.
        Route("/sse", endpoint=sse.handle_sse),
        Mount("/messages", app=sse.handle_post_message), 
    ]
)

# 3. 서버 실행 시 MCP 로직을 앱과 연결
# lifespan을 사용하여 서버 시작 시 MCP 서버를 구동합니다.
@app.on_event("startup")
async def startup():
    # 이 부분에서 MCP 서버의 초기화 옵션을 설정하고 실행 대기 상태로 만듭니다.
    # Starlette의 백그라운드 태스크나 별도 로직 없이 sse 핸들러가 이를 처리합니다.
    pass

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # Render 로그 확인용
    print(f"🚀 ShopCatch V1 Standard Live at: 0.0.0.0:{port}/sse")
    
    uvicorn.run(app, host="0.0.0.0", port=port)
