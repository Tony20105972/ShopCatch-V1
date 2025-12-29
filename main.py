import os
import json
import logging
import httpx
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
from mcp.server import Server
from mcp.server.sse import SseServerTransport

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-mcp")

load_dotenv()

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 1. MCP 서버 초기화
mcp_server = Server("shopcatch")
# Streamable HTTP도 내부적으로는 SSE 전송 방식을 빌려 쓰되, 
# 단일 엔드포인트에서 처리하도록 설정합니다.
sse_transport = SseServerTransport("/mcp") # 이 경로는 내부 식별용입니다.

@mcp_server.list_tools()
async def handle_list_tools():
    return [
        {
            "name": "recommend_and_search_products",
            "description": "네이버 쇼핑 API 상품 검색",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색어"},
                    "display": {"type": "integer", "description": "결과 수", "default": 5}
                },
                "required": ["query"]
            }
        }
    ]

@mcp_server.call_tool()
async def handle_call_tool(name, arguments):
    if name == "recommend_and_search_products":
        query = arguments.get("query")
        display = arguments.get("display", 5)
        headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://openapi.naver.com/v1/search/shop.json", headers=headers, params={"query": query, "display": display})
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                res = [f"상품: {i['title'].replace('<b>','').replace('</b>','')}\n가격: {i['lprice']}원\n링크: {i['link']}" for i in items]
                return [{"type": "text", "text": "\n\n".join(res)}]
    return [{"type": "text", "text": "에러 발생"}]

# --- 핵심: 어떤 경로로 POST가 들어와도 처리하도록 통합 ---

async def handle_everything(request):
    """Inspector가 /sse로 찌르든 /mcp로 찌르든 다 받아줌"""
    if request.method == "POST":
        # Streamable HTTP의 핵심: POST 메시지 처리
        await sse_transport.handle_post_message(request.scope, request.receive, request.send)
    else:
        # GET 요청은 연결 핸들러로
        async with sse_transport.connect_scope(request.scope, request.receive, request.send) as scope:
            await mcp_server.run(scope[0], scope[1], sse_transport.handle_sse)

# 모든 경로를 handle_everything으로 연결
app = Starlette(
    routes=[
        Route("/", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/sse", endpoint=handle_everything, methods=["GET", "POST"]),
        Route("/mcp", endpoint=handle_everything, methods=["GET", "POST"]),
    ]
)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
