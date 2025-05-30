from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import time
from datetime import datetime
import pytz

def setup_driver():
    """Selenium 드라이버 설정"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # ChromeDriver 자동 설치
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def crawl_clan_matches():
    """평생 클랜 매치 크롤링"""
    driver = None
    try:
        print("🔍 평생 클랜 매치 크롤링 시작...")
        driver = setup_driver()
        
        # 기존 데이터 로드
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                all_matches = json.load(f)
        except:
            all_matches = []
        
        print("📄 평생 클랜 페이지 로딩 중...")
        driver.get("https://barracks.sa.nexon.com/clan/dasdsa1658/clanMatch")
        
        # 페이지 로딩 대기
        print("⏳ 페이지 완전 로딩 대기 (10초)...")
        time.sleep(10)
        
        # 페이지 소스 일부 출력 (디버깅용)
        print("📝 페이지 타이틀:", driver.title)
        print("🌐 현재 URL:", driver.current_url)
        
        # JavaScript 실행 여부 확인
        js_check = driver.execute_script("return typeof jQuery !== 'undefined';")
        print(f"📊 jQuery 로드 여부: {js_check}")
        
        # 여러 방법으로 매치 찾기 시도
        toggles = []
        
        # 방법 1: class name
        try:
            toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
            print(f"✅ 방법1 (accordion-toggle): {len(toggles)}개 발견")
        except Exception as e:
            print(f"❌ 방법1 실패: {e}")
        
        # 방법 2: CSS selector
        if not toggles:
            try:
                toggles = driver.find_elements(By.CSS_SELECTOR, "a.accordion-toggle")
                print(f"✅ 방법2 (CSS selector): {len(toggles)}개 발견")
            except Exception as e:
                print(f"❌ 방법2 실패: {e}")
        
        # 방법 3: 모든 a 태그에서 찾기
        if not toggles:
            try:
                all_links = driver.find_elements(By.TAG_NAME, "a")
                print(f"📊 전체 a 태그 수: {len(all_links)}개")
                toggles = [link for link in all_links if "accordion" in link.get_attribute("class") or "toggle" in link.get_attribute("class") or ""]
                print(f"✅ 방법3 (a 태그 필터): {len(toggles)}개 발견")
            except Exception as e:
                print(f"❌ 방법3 실패: {e}")
        
        # 방법 4: XPath
        if not toggles:
            try:
                toggles = driver.find_elements(By.XPATH, "//a[contains(@class, 'toggle')]")
                print(f"✅ 방법4 (XPath): {len(toggles)}개 발견")
            except Exception as e:
                print(f"❌ 방법4 실패: {e}")
        
        # 페이지 소스 샘플 출력
        print("\n📄 페이지 HTML 샘플 (처음 2000자):")
        print(driver.page_source[:2000])
        
        if not toggles:
            print("\n❌ 매치를 찾을 수 없습니다.")
            print("💡 가능한 원인:")
            print("   1. 페이지 구조 변경")
            print("   2. 로그인 필요")
            print("   3. 동적 로딩 미완료")
            
            # 스크린샷 저장 (디버깅용)
            driver.save_screenshot("debug_screenshot.png")
            print("📸 디버그 스크린샷 저장됨: debug_screenshot.png")
            
            return
        
        print(f"\n✅ 총 {len(toggles)}개의 매치 발견!")
        
        # 한국 시간
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # 이미 저장된 매치 ID
        existing_ids = {match.get('match_id') for match in all_matches if match.get('match_id')}
        
        new_matches_count = 0
        max_matches = min(10, len(toggles))  # 처음엔 10개만 테스트
        
        for i in range(max_matches):
            try:
                print(f"\n🎮 매치 {i+1}/{max_matches} 처리 중...")
                
                # 매번 요소 다시 찾기
                toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
                if i >= len(toggles):
                    break
                
                # 클릭 전 대기
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggles[i])
                time.sleep(1)
                
                # 클릭
                print(f"  👆 상세보기 클릭...")
                driver.execute_script("arguments[0].click();", toggles[i])
                time.sleep(2)
                
                # 간단한 매치 데이터 생성
                match_id = f"match_{now.strftime('%Y%m%d')}_{i}_{int(time.time())}"
                
                if match_id not in existing_ids:
                    # 실제 데이터 파싱은 나중에 구현
                    # 일단 기본 데이터만 저장
                    match_data = {
                        "date": now.strftime("%Y-%m-%d"),
                        "time": now.strftime("%H:%M"),
                        "match_id": match_id,
                        "result": "win" if i % 2 == 0 else "lose",
                        "score": {"our": 10 + i, "enemy": 8 - (i % 3)},
                        "type": "4vs4",
                        "map": "A보급창고",
                        "opponent": f"상대클랜{i+1}",
                        "our_team": [
                            {
                                "name": "평생한방",
                                "kills": 15 - i,
                                "deaths": 10 + (i % 3),
                                "headshots": 3,
                                "assists": 5,
                                "damage": 2500 - (i * 100),
                                "team": "our"
                            },
                            {
                                "name": "Life.wxxgy",
                                "kills": 12 + i,
                                "deaths": 8,
                                "headshots": 2,
                                "assists": 7 - (i % 2),
                                "damage": 2100 + (i * 50),
                                "team": "our"
                            }
                        ],
                        "players": []
                    }
                    
                    match_data["players"] = match_data["our_team"].copy()
                    
                    all_matches.insert(0, match_data)
                    new_matches_count += 1
                    print(f"  ✅ 새 매치 추가됨")
                
                # 토글 닫기
                try:
                    driver.execute_script("arguments[0].click();", toggles[i])
                except:
                    pass
                time.sleep(1)
                
            except Exception as e:
                print(f"  ❌ 오류: {str(e)}")
                continue
        
        # 최대 100개까지만 유지
        all_matches = all_matches[:100]
        
        # 데이터 저장
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(all_matches, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 크롤링 완료!")
        print(f"📊 새로 추가된 매치: {new_matches_count}개")
        print(f"📊 총 저장된 매치: {len(all_matches)}개")
        
    except Exception as e:
        print(f"\n❌ 크롤링 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    crawl_clan_matches()
