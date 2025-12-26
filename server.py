import os
import httpx
from mcp.server import Server
import mcp.types as types
from dotenv import load_dotenv

load_dotenv()

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# MCP 서버 초기화
server = Server("shop-catch")

@server.list_tools()
async def handle_list_tools():
    """챗봇에게 제공할 도구 목록 정의"""
    return [
        types.Tool(
            name="search_naver_shopping",
            description="네이버 쇼핑에서 키워드로 최저가 상품을 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 상품명"},
                    "display": {"type": "number", "description": "가져올 결과 개수 (1-10)", "default": 5},
                },
                "required": ["query"],
            },
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """실제 도구 실행 로직"""
    if name == "search_naver_shopping":
        query = arguments.get("query")
        display = arguments.get("display", 5)

        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                params={"query": query, "display": display},
                headers=headers
            )
            
            if response.status_code != 200:
                return [types.TextContent(type="text", text=f"❌ 네이버 API 에러: {response.text}")]
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                return [types.TextContent(type="text", text="🔍 검색 결과가 없습니다.")]
            
            # 결과 포맷팅
            formatted_results = []
            for item in items:
                title = item['title'].replace("<b>", "").replace("</b>", "")
                formatted_results.append(f"🛍️ {title}\n💰 최저가: {item['lprice']}원\n🔗 링크: {item['link']}\n")
            
            return [types.TextContent(type="text", text="\n".join(formatted_results))]
