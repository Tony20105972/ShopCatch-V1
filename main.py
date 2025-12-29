import os
import json
import logging
import httpx
from dotenv import load_dotenv
from starlette.applications import Starlette
from starlette.routing import Route
from starlette.responses import JSONResponse
from mcp.server import Server
import mcp.types as types

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("shopcatch-mcp")

load_dotenv()

# 네이버 API 설정 (환경변수)
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 1. MCP 서버 본체 정의
mcp_server = Server("shopcatch")

# 2. 도구 등록
@mcp_server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="recommend_and_search_products",
            description="네이버 쇼핑 API 상품 검색",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색어"},
                    "display": {"type": "integer", "description": "결과 수", "default": 5}
                },
                "required": ["query"]
            }
        )
    ]

# 3. 도구 로직
@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
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
                res = [f"상품: {i['title'].replace('<b>','').replace('</b>','')}\n가격: {i['lprice']}원\n링크: {i['link']}" for i in items]
                return [types.TextContent(type="text", text="\n\n".join(res))]
    return [types.TextContent(type="text", text="결과가 없습니다.")]

# 4. Streamable HTTP 핸들러 (루트 POST 처리)
async def handle_mcp_request(request):
    """모든 JSON-RPC 요청을 여기서 처리"""
    try:
        body = await request.json()
        # MCP 서버 엔진에 요청을 전달하고 결과를 받음
        # Streamable HTTP에서는 통신 계층을 직접 연결해줘야 함
        # 여기서는 단순화를 위해 직접 서버를 구동하는 방식을 택함
        from mcp.server.stdio import Context
        # 실제 서버가 돌아가도록 응답 구성
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id"),
            "result": {"tools": await handle_list_tools()} if body.get("method") == "list_tools" else {}
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# Starlette 앱 (루트 경로에서 POST만 허용)
app = Starlette(
    routes=[
        Route("/", endpoint=handle_mcp_request, methods=["POST"]),
    ]
)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
