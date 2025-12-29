import os
import json
import logging
import anyio
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport
import httpx
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-mcp")

load_dotenv()

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# MCP 서버 초기화
mcp_server = Server("shopcatch")
sse_transport = SseServerTransport("/messages")

@mcp_server.list_tools()
async def handle_list_tools():
    return [
        {
            "name": "recommend_and_search_products",
            "description": "네이버 쇼핑 API를 사용하여 상품을 검색하고 추천합니다.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 상품명"},
                    "display": {"type": "integer", "description": "결과 수", "default": 5}
                },
                "required": ["query"]
            }
        }
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "recommend_and_search_products":
        query = arguments.get("query")
        display = arguments.get("display", 5)
        
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                headers=headers,
                params={"query": query, "display": display}
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                res = [f"상품: {i['title']}\n가격: {i['lprice']}원\n링크: {i['link']}" for i in items]
                return [{"type": "text", "text": "\n\n".join(res)}]
    return [{"type": "text", "text": "Error"}]

# --- 엔드포인트 핸들러 ---
async def handle_sse(request):
    async with sse_transport.connect_scope(request.scope, request.receive, request.send) as scope:
        await mcp_server.run(scope[0], scope[1], sse_transport.handle_sse)

async def handle_messages(request):
    await sse_transport.handle_post_message(request.scope, request.receive, request.send)

async def homepage(request):
    return JSONResponse({"status": "running"})

# Starlette 앱 설정
app = Starlette(
    routes=[
        Route("/", endpoint=homepage),
        Route("/sse", endpoint=handle_sse, methods=["GET"]),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
