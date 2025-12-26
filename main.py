import os
import uvicorn
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from mcp.server.sse import SseServerTransport
from server import server  # server.py의 server 객체

# ✅ 최신 버전 핵심: 생성 시 server 객체를 넘겨줍니다.
sse = SseServerTransport("/messages", server=server)

# Starlette 앱 정의
app = Starlette(
    routes=[
        # ✅ handle_sse 속성이 없는 경우를 대비해 직접 호출하는 대신 
        # sse 객체의 메서드를 안전하게 바인딩합니다.
        Route("/sse", endpoint=sse.handle_sse),
        Mount("/messages", app=sse.handle_post_message),
    ]
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print(f"🚀 ShopCatch V1 Standard Live: 0.0.0.0:{port}/sse")
    uvicorn.run(app, host="0.0.0.0", port=port)
