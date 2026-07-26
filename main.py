import os
import requests
import json
import html
import yfinance as yf
from datetime import datetime

# ---------------------------------------------------------
# 1. 깃허브 비밀키 
# ---------------------------------------------------------
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

# 💡 국내 주식 코드 뒤에 '.KS'를 붙여서 야후 파이낸스용으로 변경
KR_STOCKS = {'삼성전자': '005930.KS', '현대차': '005380.KS', 'NAVER': '035420.KS', '현대제철': '004020.KS', '한화솔루션': '009830.KS'}
US_STOCKS = {'엔비디아': 'NVDA', '테슬라': 'TSLA', '알파벳A': 'GOOGL'}

# ---------------------------------------------------------
# 2. 핵심 함수들
# ---------------------------------------------------------
def get_new_kakao_token():
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }
    res = requests.post(url, data=data).json()
    return res.get("access_token")

def get_stock_info(ticker_symbol):
    """국내/해외 주가를 모두 yfinance 하나로 가져옵니다."""
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="5d")
    
    # 주말/휴장일 nan(빈칸) 데이터 제거
    hist = hist.dropna(subset=['Close']) 
    
    if len(hist) >= 2:
        prev_close = hist['Close'].iloc[-2]
        curr_close = hist['Close'].iloc[-1]
        change_percent = ((curr_close - prev_close) / prev_close) * 100
        return curr_close, round(change_percent, 2)
    return None, None

def get_naver_news(keyword):
    search_query = f"{keyword} 주가"
    url = f"https://openapi.naver.com/v1/search/news.json?query={search_query}&display=2&sort=sim"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    res = requests.get(url, headers=headers)
    
    if res.status_code == 200:
        items = res.json().get('items', [])
        news_list = []
        for item in items:
            clean_title = html.unescape(item['title']).replace('<b>', '').replace('</b>', '')
            news_list.append(clean_title)
        return news_list
    return ["관련 뉴스를 불러오지 못했습니다."]

def send_kakao_message(access_token, text):
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    template = {
        "object_type": "text",
        "text": text,
        "link": {
            "web_url": "https://m.stock.naver.com",
            "mobile_web_url": "https://m.stock.naver.com"
        }
    }
    
    payload = {"template_object": json.dumps(template)}
    requests.post(url, headers=headers, data=payload)

# ---------------------------------------------------------
# 3. 메인 실행
# ---------------------------------------------------------
def main():
    access_token = get_new_kakao_token()
    if not access_token:
        print("토큰 갱신 실패!")
        return
        
    report = ["📈 [오늘의 주식 포트폴리오]\n\n🇰🇷 [국내 주식]"]
    
    # 국내 주식 파트
    for name, ticker in KR_STOCKS.items():
        price, change = get_stock_info(ticker)
        if price:
            sign = "+" if change > 0 else ""
            report.append(f"• {name}: {int(price):,}원 ({sign}{change:.2f}%)")
            for n in get_naver_news(name):
                report.append(f"  - {n}")
        else:
            report.append(f"• {name}: 데이터 없음")
            
    report.append("\n🇺🇸 [해외 주식]")
    
    # 해외 주식 파트
    for name, ticker in US_STOCKS.items():
        price, change = get_stock_info(ticker)
        if price:
            sign = "+" if change > 0 else ""
            report.append(f"• {name}: ${round(price, 2)} ({sign}{change:.2f}%)")
        else:
            report.append(f"• {name}: 데이터 없음")

    final_text = "\n".join(report)
    final_text = final_text.replace('"', "'")
    
    send_kakao_message(access_token, final_text)

if __name__ == "__main__":
    main()
