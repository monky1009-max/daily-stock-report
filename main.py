import os
import requests
from pykrx import stock
import yfinance as yf
from datetime import datetime, timedelta

# ---------------------------------------------------------
# 1. 깃허브에서 가져올 비밀키 설정
# ---------------------------------------------------------
KAKAO_REST_API_KEY = os.environ.get("KAKAO_REST_API_KEY")
KAKAO_REFRESH_TOKEN = os.environ.get("KAKAO_REFRESH_TOKEN")
NAVER_CLIENT_ID = os.environ.get("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET")

# ---------------------------------------------------------
# 2. 포트폴리오 종목 세팅
# ---------------------------------------------------------
KR_STOCKS = {'삼성전자': '005930', '현대차': '005380', 'NAVER': '035420', '현대제철': '004020', '한화솔루션': '009830'}
US_STOCKS = {'엔비디아': 'NVDA', '테슬라': 'TSLA', '알파벳A': 'GOOGL'}

# ---------------------------------------------------------
# 3. 핵심 기능 함수들
# ---------------------------------------------------------
def get_new_kakao_token():
    """리프레시 토큰을 이용해 1회용 액세스 토큰 재발급"""
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "refresh_token",
        "client_id": KAKAO_REST_API_KEY,
        "refresh_token": KAKAO_REFRESH_TOKEN
    }
    res = requests.post(url, data=data).json()
    return res.get("access_token")

def get_kr_stock_info(code):
    """pykrx로 최근 영업일 국내 주가 수집"""
    today = datetime.today()
    start_date = (today - timedelta(days=7)).strftime("%Y%m%d")
    end_date = today.strftime("%Y%m%d")
    df = stock.get_market_ohlcv(start_date, end_date, code)
    if not df.empty:
        close = df['종가'].iloc[-1]
        change = df['등락률'].iloc[-1]
        return close, change
    return None, None

def get_us_stock_info(ticker_symbol):
    """yfinance로 해외 주가 수집"""
    ticker = yf.Ticker(ticker_symbol)
    hist = ticker.history(period="5d")
    if len(hist) >= 2:
        prev_close = hist['Close'].iloc[-2]
        curr_close = hist['Close'].iloc[-1]
        change_percent = ((curr_close - prev_close) / prev_close) * 100
        return round(curr_close, 2), round(change_percent, 2)
    return None, None

def get_naver_news(keyword):
    """네이버 API로 최신 뉴스 헤드라인 2개 수집"""
    url = f"https://openapi.naver.com/v1/search/news.json?query={keyword}&display=2&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        items = res.json().get('items', [])
        return [item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"') for item in items]
    return ["관련 뉴스를 불러오지 못했습니다."]

def send_kakao_message(access_token, text):
    """카카오톡 나에게 보내기"""
    url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "template_object": f'''{{
            "object_type": "text",
            "text": "{text}",
            "link": {{"web_url": "https://m.stock.naver.com"}}
        }}'''
    }
    res = requests.post(url, headers=headers, data=payload)
    return res.status_code

# ---------------------------------------------------------
# 4. 메인 리포트 생성 및 전송
# ---------------------------------------------------------
def main():
    access_token = get_new_kakao_token()
    if not access_token:
        print("토큰 갱신 실패!")
        return

    report = ["📈 [오늘의 주식 포트폴리오]\n\n🇰🇷 [국내 주식]"]
    
    for name, code in KR_STOCKS.items():
        price, change = get_kr_stock_info(code)
        if price:
            sign = "+" if change > 0 else ""
            report.append(f"• {name}: {int(price):,}원 ({sign}{change:.2f}%)")
            for n in get_naver_news(name):
                report.append(f"  - {n}")
        else:
            report.append(f"• {name}: 주가 정보 없음")
            
    report.append("\n🇺🇸 [해외 주식]")
    for name, ticker in US_STOCKS.items():
        price, change = get_us_stock_info(ticker)
        if price:
            sign = "+" if change > 0 else ""
            report.append(f"• {name}: ${price} ({sign}{change:.2f}%)")
        else:
            report.append(f"• {name}: 주가 정보 없음")

    final_text = "\n".join(report)
    # 카카오 API는 일부 특수문자에 민감하므로 큰따옴표를 홑따옴표로 변경
    final_text = final_text.replace('"', "'") 
    
    send_kakao_message(access_token, final_text)

if __name__ == "__main__":
    main()
