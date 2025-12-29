import os
import json
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
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
app = FastAPI(title="ShopCatch MCP Server")
mcp_server = Server("shopcatch")
sse_transport = SseServerTransport("/messages")

@mcp_server.list_tools()
async def handle_list_tools():
    """사용 가능한 도구 목록 반환"""
    return [
        {
            "name": "recommend_and_search_products",
            "description": "네이버 쇼핑 API를 사용하여 상품을 검색하고 추천합니다.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "검색할 상품명 (예: 20대 남성 시계)"},
                    "display": {"type": "integer", "description": "검색 결과 수 (1~100)", "default": 5}
                },
                "required": ["query"]
            }
        }
    ]

@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    """도구 실행 로직"""
    if name == "recommend_and_search_products":
        query = arguments.get("query")
        display = arguments.get("display", 5)

        url = "https://openapi.naver.com/v1/search/shop.json"
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
        }
        params = {"query": query, "display": display}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])
                results = []
                for item in items:
                    # HTML 태그 제거 및 결과 정리
                    title = item['title'].replace("<b>", "").replace("</b>", "")
                    results.append(f"상품명: {title}\n가격: {item['lprice']}원\n링크: {item['link']}\n")
                
                return [{"type": "text", "text": "\n".join(results)}]
            else:
                return [{"type": "text", "text": f"네이버 API 에러: {response.status_code}"}]

    raise ValueError(f"Unknown tool: {name}")

# --- MCP Transport Routes ---

@app.get("/sse")
async def handle_sse(request: Request):
    """SSE 연결 엔드포인트"""
    async with sse_transport.connect_scope(request.scope, request.receive, request.send) as scope:
        await mcp_server.run(
            scope[0],
            scope[1],
            sse_transport.handle_sse
        )

@app.post("/messages")
async def handle_messages(request: Request):
    """메시지 수신 엔드포인트"""
    await sse_transport.handle_post_message(request.scope, request.receive, request.send)

@app.get("/")
async def root():
    """서버 상태 확인용"""
    return {"status": "running", "mcp_endpoint": "/sse"}

# --- 포트 바인딩 및 실행 ---
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
