import os
import httpx
import logging
import mcp.types as types
from mcp.server import Server
from dotenv import load_dotenv

load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gift-catch-server")

# 네이버 API 설정
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# MCP 서버 초기화
server = Server("shop-catch")

@server.list_tools()
async def handle_list_tools():
    """
    사용자의 복잡한 문장형 요청(Natural Language)을 처리하기 위해 
    도구의 Description을 최적화했습니다.
    """
    return [
        types.Tool(
            name="curate_gift_recommendations",
            description=(
                "사용자의 대화 문맥에서 대상, 상황, 예산, 취향을 분석하여 최적의 선물을 추천합니다. "
                "예: '부모님 환갑 선물로 20만원대 안마기 찾아줘'와 같은 문장형 요청에 최적화되어 있습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string", "description": "선물 받는 사람 (예: 60대 어머니, 신입사원)"},
                    "occasion": {"type": "string", "description": "선물 목적 (예: 환갑, 취업 축하, 결혼기념일)"},
                    "max_price": {"type": "number", "description": "최대 예산 (원 단위)"},
                    "min_price": {"type": "number", "description": "최소 예산 (원 단위)", "default": 0},
                    "preference": {"type": "string", "description": "스타일/취향 (예: 고급스러운, 실용적인, 가성비)"},
                    "full_context": {"type": "string", "description": "사용자의 전체 요청 문장 (분석 보조용)"}
                },
                "required": ["recipient", "occasion"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict):
    if name == "curate_gift_recommendations":
        recipient = arguments.get("recipient")
        occasion = arguments.get("occasion")
        max_price = arguments.get("max_price")
        min_price = arguments.get("min_price", 0)
        preference = arguments.get("preference", "")
        full_context = arguments.get("full_context", "")

        # 1. 자연어 문맥을 반영한 고성능 쿼리 조합
        # 사용자의 전체 문장을 쿼리에 섞어 네이버 검색의 정확도를 극대화함
        search_query = f"{recipient} {occasion} 선물 {preference} {full_context}".strip()
        
        headers = {
            "X-Naver-Client-Id": NAVER_CLIENT_ID,
            "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
        }
        
        # 네이버 API lprice, hprice 파라미터를 활용해 서버 사이드 필터링 강화
        params = {
            "query": search_query,
            "display": 20, 
            "sort": "sim"
        }
        if min_price: params["lprice"] = int(min_price)
        if max_price: params["hprice"] = int(max_price)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openapi.naver.com/v1/search/shop.json",
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                return [types.TextContent(type="text", text="❌ 쇼핑 API 연결에 실패했습니다.")]
            
            data = response.json()
            items = data.get("items", [])
            
            if not items:
                price_range = f" ({min_price:,}원~{max_price:,}원)" if max_price else ""
                return [types.TextContent(type="text", text=f"🔍 요청하신 조건{price_range}에 딱 맞는 선물을 찾지 못했습니다.")]

            # 2. 결과 큐레이션 및 포맷팅
            formatted_results = [
                f"🤖 **선물 에이전트의 맞춤 큐레이션**\n",
                f"'{recipient}'님을 위한 '{occasion}' 선물로 다음 상품들을 추천합니다.\n"
            ]
            
            for i, item in enumerate(items[:5]):
                title = item['title'].replace("<b>", "").replace("</b>", "")
                price = int(item['lprice'])
                mall = item.get('mallName', '네이버쇼핑')
                
                formatted_results.append(
                    f"{i+1}. **{title}**\n"
                    f"   💰 가격: {price:,}원 | 🏬 판매처: {mall}\n"
                    f"   🔗 [상품 바로가기]({item['link']})\n"
                )
            
            # 3. 고성능 번들링(Bundle) 제안 기능
            # 예산이 넉넉할 경우 두 가지 상품의 조합을 제안하여 에이전트의 지능을 강조
            if len(items) >= 2 and max_price:
                p1, p2 = int(items[0]['lprice']), int(items[1]['lprice'])
                if p1 + p2 <= max_price:
                    t1 = items[0]['title'].replace("<b>", "").replace("</b>", "")
                    t2 = items[1]['title'].replace("<b>", "").replace("</b>", "")
                    formatted_results.append(
                        f"\n✨ **에이전트의 플러스 제안**\n"
                        f"예산 범위 내에서 '{t1}'와(과) '{t2}'를 함께 구성하여 "
                        f"더욱 풍성한 선물 세트를 만들어보시는 건 어떨까요?"
                    )

            return [types.TextContent(type="text", text="\n".join(formatted_results))]

    return [types.TextContent(type="text", text="알 수 없는 요청입니다.")]
