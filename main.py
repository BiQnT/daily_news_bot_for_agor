import os
import smtplib
import feedparser
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv

# 로컬 테스트용 .env 파일 로드
load_dotenv()

# --- 설정값 ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

# 관심 키워드 (블록체인 & 규제 중심)
KEYWORDS = [
    "Blockchain Scalability",      
    "Zero Knowledge Proof",        
    "Modular Blockchain",          
    "Stablecoin Regulation",       
    "Crypto Payment Infrastructure", 
    "CBDC vs Stablecoin",          
    "금융위원회 가상자산",          
    "가상자산 이용자 보호법",       
    "토큰 증권 STO"                
]

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_news_rss(keyword):
    """
    구글 뉴스 RSS에서 키워드 검색 후, 
    '최근 7일 이내'의 뉴스만 필터링하여 최대 3개를 반환합니다.
    """
    encoded_keyword = keyword.replace(" ", "+")
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=ko&gl=KR&ceid=KR:ko"
    
    feed = feedparser.parse(url)
    articles = []
    
    # 기준 날짜 설정 (현재 시간 - 7일)
    one_week_ago = datetime.now() - timedelta(days=7)
    
    for entry in feed.entries:
        # 뉴스 항목에 발행일 정보가 있는지 확인
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            # feedparser의 시간 구조체(struct_time)를 datetime 객체로 변환
            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            
            # 7일 이내 기사인지 확인
            if pub_date >= one_week_ago:
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "pubDate": entry.published
                })
        else:
            # 날짜 정보가 없으면 일단 포함 (드문 경우)
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "pubDate": "날짜 정보 없음"
            })

        # 유효한 기사가 3개가 차면 중단 (너무 많이 가져오면 비용/시간 낭비)
        if len(articles) >= 3:
            break
            
    return articles

def summarize_article(title, link):
    """GPT-4o-mini를 사용하여 뉴스 제목과 링크를 기반으로 요약합니다."""
    prompt = f"""
    뉴스 제목: {title}
    링크: {link}
    
    위 뉴스의 핵심 내용을 예상하여 한 문장으로 요약하고, 
    이것이 블록체인/핀테크 연구원에게 미칠 시사점(Insight)을 한 문장으로 덧붙여줘.
    형식:
    - 요약: ...
    - 인사이트: ...
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful blockchain tech analyst."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 실패: {str(e)}"

def send_email(subject, html_content):
    """HTML 형식의 이메일을 발송합니다."""
    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject

    msg.attach(MIMEText(html_content, 'html'))

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_TO, msg.as_string())
        server.quit()
        print("✅ 이메일 발송 성공!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {str(e)}")

def main():
    print("뉴스 수집 및 요약 시작...")
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # 이메일 본문 시작
    email_html = f"<h2>📅 {today_date} Blockchain & Tech Briefing</h2><hr>"
    
    news_found = False # 뉴스가 하나라도 있었는지 체크

    for keyword in KEYWORDS:
        print(f"🔍 '{keyword}' 검색 중...")
        articles = fetch_news_rss(keyword)
        
        if not articles:
            continue
            
        news_found = True
        email_html += f"<h3 style='color: #2E86C1;'>#{keyword}</h3><ul>"
        
        for article in articles:
            summary = summarize_article(article['title'], article['link'])
            email_html += f"""
            <li style='margin-bottom: 15px;'>
                <a href='{article['link']}' style='font-weight: bold; font-size: 16px;'>{article['title']}</a>
                <span style='font-size: 12px; color: gray;'>({article['pubDate']})</span><br>
                <p style='background-color: #f4f4f4; padding: 10px; border-radius: 5px; font-size: 14px;'>
                    {summary.replace(chr(10), '<br>')}
                </p>
            </li>
            """
        email_html += "</ul><br>"

    email_html += "<hr><p style='font-size: 12px; color: gray;'>This email was generated by AI Agent.</p>"
    
    if news_found:
        send_email(f"[Daily BlockChain News] {today_date} 뉴스 요약", email_html)
    else:
        print("📭 최근 7일간 새로운 뉴스가 없어 메일을 보내지 않았습니다.")

if __name__ == "__main__":
    main()