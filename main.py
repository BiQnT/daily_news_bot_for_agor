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

# --- 관심 키워드 설정 (IUPAC 2025 & 유망 산업) ---
# 검색 품질을 위해 글로벌 통용되는 '영문 키워드'를 사용합니다.
KEYWORDS = [
    # [Group 1] IUPAC 2025 Emerging Technologies
    "Xolography",                         # 크로로그래피 (차세대 3D 프린팅)
    "Single-Atom Catalysis",              # 단일 원자 촉매
    "Nanochain Biosensor",                # 나노체인 바이오센서
    "Carbon Dots",                        # 탄소 점 (나노 소재)
    "Synthetic Cells",                    # 합성 세포
    "Thermogelling Polymers",             # 열반응 겔화 고분자
    "Electrochemical CO2 Capture",        # 전기화학적 이산화탄소 포집
    "Multimodal Foundation Models Science", # 과학용 복합 모달 모델 (AI)
    "Direct Air Capture",                 # 직접 공기 포집 (DAC)
    "Additive Manufacturing",             # 적층 제조

    # [Group 2] Industry & Research Trends
    "Sustainable Green Chemistry",        # 친환경 지속가능 화학
    "AI-driven Drug Discovery",           # AI 신약 개발
    "Solid-state Battery Materials",      # 전고체 등 차세대 배터리 소재
    "Semiconductor Specialty Chemicals",  # 반도체 특수 화학 소재
    "CCUS Technology",                    # 탄소 포집/활용/저장
]

client = OpenAI(api_key=OPENAI_API_KEY)

def fetch_news_rss(keyword):
    """
    최근 7일 이내 뉴스 필터링.
    전문 용어는 영어 뉴스가 많으므로 gl=US(미국) 설정도 고려 가능하나,
    일단 국내외 통합 검색을 위해 언어 설정을 풉니다.
    """
    encoded_keyword = keyword.replace(" ", "+")
    # ceid, gl, hl 파라미터를 조정하여 글로벌(영어 포함) 뉴스를 가져오도록 설정
    # hl=en: 영어 인터페이스, gl=US: 미국 기준 (가장 기술 뉴스가 많음)
    url = f"https://news.google.com/rss/search?q={encoded_keyword}&hl=en-US&gl=US&ceid=US:en"
    
    feed = feedparser.parse(url)
    articles = []
    # 타임존 이슈를 피하기 위해 단순 비교 (UTC 기준)
    one_week_ago = datetime.now() - timedelta(days=7)
    
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            if pub_date >= one_week_ago:
                articles.append({
                    "title": entry.title,
                    "link": entry.link,
                    "pubDate": pub_date.strftime("%Y.%m.%d")
                })
        else:
            # 날짜 없는 경우도 포함 (최신순 정렬이므로 상위는 보통 최신임)
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "pubDate": "Recent"
            })

        # 너무 많은 뉴스를 방지하기 위해 키워드 당 2개로 제한 (전체 키워드가 많으므로)
        if len(articles) >= 2:
            break
            
    return articles

def summarize_article(title, link):
    """GPT 요약 요청 (결과는 한국어로)"""
    prompt = f"""
    Article Title: {title}
    Link: {link}
    
    Please analyze this technical article.
    1. Summarize the core technology or finding in 2 lines (Korean).
    2. Provide 1 sentence of insight for a chemical engineering/material science researcher (Korean).
    
    Format:
    요약: [Summary in Korean]
    인사이트: [Insight in Korean]
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an expert researcher in chemistry and advanced materials."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"요약 실패: {str(e)}"

def send_email(subject, html_content):
    """이메일 전송"""
    msg = MIMEMultipart()
    msg['From'] = "POSTECH Tech Radar <" + EMAIL_USER + ">"
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
    print("🔬 IUPAC 2025 및 첨단 기술 뉴스 브리핑 생성 시작...")
    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    # 디자인: POSTECH Red (#C80150)
    email_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', 'Helvetica Neue', sans-serif; background-color: #F2F4F6; margin: 0; padding: 0; }}
            .container {{ max-width: 650px; margin: 30px auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px rgba(0,0,0,0.05); }}
            
            /* 헤더 */
            .header {{ background: linear-gradient(135deg, #C80150 0%, #8A0030 100%); color: #ffffff; padding: 40px 30px; }}
            .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; }}
            .header p {{ margin: 8px 0 0; font-size: 14px; font-weight: 300; opacity: 0.9; }}
            
            .content {{ padding: 30px; }}
            
            /* 섹션 */
            .keyword-section {{ margin-bottom: 35px; }}
            .keyword-header {{ display: flex; align-items: center; margin-bottom: 12px; border-bottom: 2px solid #C80150; padding-bottom: 8px; }}
            .keyword-badge {{ background-color: #C80150; color: white; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-right: 10px; text-transform: uppercase; }}
            .keyword-title {{ color: #C80150; font-size: 16px; font-weight: 700; }}
            
            /* 카드 */
            .article-card {{ background-color: #ffffff; margin-bottom: 20px; }}
            .article-title {{ font-size: 17px; font-weight: 700; color: #222; text-decoration: none; display: block; line-height: 1.4; margin-bottom: 5px; }}
            .article-title:hover {{ color: #C80150; text-decoration: underline; }}
            .article-meta {{ font-size: 12px; color: #888; margin-bottom: 10px; display: block; }}
            
            /* 요약 & 인사이트 */
            .summary-box {{ background-color: #FAFAFA; border-left: 3px solid #C80150; padding: 12px 15px; font-size: 14px; line-height: 1.6; color: #333; }}
            .insight-box {{ margin-top: 10px; background-color: #FEF2F5; border: 1px solid #FADADD; padding: 10px 12px; border-radius: 6px; font-size: 13px; color: #555; display: flex; }}
            .insight-icon {{ margin-right: 8px; }}
            .insight-label {{ font-weight: bold; color: #C80150; font-size: 11px; margin-right: 5px; }}

            .footer {{ background-color: #f2f4f6; text-align: center; padding: 30px; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Chemistry & Tech Trends</h1>
                <p>{today_date} | IUPAC 2025 Emerging Tech & Industry</p>
            </div>
            <div class="content">
    """
    
    news_count = 0

    for keyword in KEYWORDS:
        print(f"🔍 '{keyword}' 검색 중...")
        articles = fetch_news_rss(keyword)
        
        if not articles:
            continue
            
        news_count += 1
        email_html += f"""
        <div class="keyword-section">
            <div class="keyword-header">
                <span class="keyword-badge">TREND</span>
                <span class="keyword-title">{keyword}</span>
            </div>
        """
        
        for article in articles:
            raw_text = summarize_article(article['title'], article['link'])
            
            summary_text = raw_text
            insight_text = ""
            
            if "인사이트:" in raw_text:
                parts = raw_text.split("인사이트:")
                summary_text = parts[0].replace("요약:", "").strip()
                insight_text = parts[1].strip()
            else:
                summary_text = raw_text.replace("요약:", "").strip()

            email_html += f"""
            <div class="article-card">
                <a href="{article['link']}" class="article-title">{article['title']}</a>
                <span class="article-meta">{article['pubDate']}</span>
                <div class="summary-box">
                    {summary_text}
                    {f'''
                    <div class="insight-box">
                        <span class="insight-icon">💡</span>
                        <div>
                            <span class="insight-label">INSIGHT</span>
                            {insight_text}
                        </div>
                    </div>
                    ''' if insight_text else ''}
                </div>
            </div>
            """
        email_html += "</div>"

    email_html += """
            </div>
            <div class="footer">
                <p>Powered by OpenAI GPT-4o & Google News</p>
                <p>© 2025 Tech Radar Bot</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    if news_count > 0:
        send_email(f"[Tech Radar] {today_date} 신기술 및 산업 동향", email_html)
    else:
        print("📭 새로운 뉴스가 없습니다.")

if __name__ == "__main__":
    main()
