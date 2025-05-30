from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
import time
from datetime import datetime
import pytz
import re

def setup_driver():
    """Selenium 드라이버 설정"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def extract_match_time(match_row):
    """매치 시간 추출"""
    try:
        # 시간 텍스트 찾기 (예: "12분 전", "1시간 전", "2025.05.29")
        time_elements = match_row.find_elements(By.TAG_NAME, "td")
        for elem in time_elements:
            text = elem.text.strip()
            if "분 전" in text or "시간 전" in text or "." in text:
                return text
    except:
        pass
    return None

def parse_player_row(row):
    """플레이어 행 파싱"""
    try:
        cells = row.find_elements(By.TAG_NAME, "td")
        if len(cells) >= 7:
            # 닉네임이 첫 번째 셀에 있는지 확인
            name = cells[0].text.strip()
            if not name or name in ["승리", "패배", "승", "패", "팀 합산 기록"]:
                return None
                
            return {
                "name": name,
                "kills": int(cells[1].text.strip() or 0),
                "deaths": int(cells[2].text.strip() or 0),
                "headshots": int(cells[3].text.strip() or 0),
                "assists": int(cells[4].text.strip() or 0),
                "saves": int(cells[5].text.strip() or 0),
                "damage": int(cells[6].text.strip().replace(",", "") or 0)
            }
    except Exception as e:
        print(f"플레이어 행 파싱 오류: {e}")
    return None

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
        
        # 이미 저장된 매치 ID 목록
        existing_ids = {match.get('match_id') for match in all_matches if match.get('match_id')}
        
        print("📄 평생 클랜 페이지 로딩 중...")
        driver.get("https://barracks.sa.nexon.com/clan/dasdsa1658/clanMatch")
        
        # 페이지 완전 로딩 대기
        wait = WebDriverWait(driver, 20)
        time.sleep(5)
        
        # 상세보기 버튼 찾기
        try:
            # JavaScript로 직접 찾기
            toggles = driver.execute_script("""
                return Array.from(document.querySelectorAll('.accordion-toggle'));
            """)
            print(f"✅ {len(toggles)}개의 매치 발견")
        except:
            toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
            print(f"✅ {len(toggles)}개의 매치 발견 (대체 방법)")
        
        if not toggles:
            print("❌ 매치를 찾을 수 없습니다.")
            return
        
        # 한국 시간
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        new_matches_count = 0
        max_matches = min(30, len(toggles))  # 최대 30개 처리
        
        for i in range(max_matches):
            try:
                print(f"\n🎮 매치 {i+1}/{max_matches} 처리 중...")
                
                # 매번 요소 다시 찾기 (DOM 변경 대응)
                toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
                if i >= len(toggles):
                    break
                
                # 매치 시간 정보 먼저 추출
                match_row = toggles[i].find_element(By.XPATH, "./ancestor::tr")
                time_text = extract_match_time(match_row)
                
                # 상세보기 클릭
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", toggles[i])
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", toggles[i])
                time.sleep(1.5)
                
                # 매치 상세 정보가 있는 tbody 찾기
                # 클릭한 토글 다음에 나타나는 상세 정보 찾기
                detail_xpath = f"(//a[@class='accordion-toggle'])[{i+1}]/ancestor::tr/following-sibling::tr[1]//tbody"
                
                try:
                    detail_tbody = driver.find_element(By.XPATH, detail_xpath)
                except:
                    # 대체 방법
                    all_tbodies = driver.find_elements(By.TAG_NAME, "tbody")
                    detail_tbody = None
                    for tbody in all_tbodies:
                        if tbody.is_displayed() and len(tbody.find_elements(By.TAG_NAME, "tr")) > 3:
                            detail_tbody = tbody
                            break
                
                if not detail_tbody:
                    print("  ⚠️ 매치 상세 정보를 찾을 수 없음")
                    # 토글 닫기
                    driver.execute_script("arguments[0].click();", toggles[i])
                    time.sleep(0.5)
                    continue
                
                # 매치 데이터 초기화
                match_data = {
                    "date": now.strftime("%Y-%m-%d"),
                    "time": time_text or now.strftime("%H:%M"),
                    "match_id": f"match_{now.strftime('%Y%m%d')}_{i}_{int(time.time())}",
                    "our_team": [],
                    "enemy_team": [],
                    "players": []
                }
                
                # 모든 행 파싱
                rows = detail_tbody.find_elements(By.TAG_NAME, "tr")
                current_team = None
                our_score = 0
                enemy_score = 0
                
                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if not cells:
                        continue
                    
                    first_cell = cells[0].text.strip()
                    
                    # 팀 구분
                    if first_cell in ["승리", "승"]:
                        current_team = "our"
                        match_data["result"] = "win"
                        continue
                    elif first_cell in ["패배", "패"]:
                        current_team = "our"
                        match_data["result"] = "lose"
                        continue
                    elif first_cell in ["gear", "적팀", "상대팀", "enemy"]:
                        current_team = "enemy"
                        continue
                    
                    # 팀 합산 기록
                    if "팀 합산" in first_cell:
                        try:
                            score = int(cells[1].text.strip())
                            if current_team == "our":
                                our_score = score
                            else:
                                enemy_score = score
                        except:
                            pass
                        continue
                    
                    # 플레이어 데이터 파싱
                    player = parse_player_row(row)
                    if player and current_team:
                        player["team"] = current_team
                        match_data["players"].append(player)
                        
                        if current_team == "our":
                            match_data["our_team"].append(player)
                        else:
                            match_data["enemy_team"].append(player)
                
                # 점수 설정
                match_data["score"] = {"our": our_score, "enemy": enemy_score}
                
                # 매치 타입 설정
                our_count = len(match_data["our_team"])
                enemy_count = len(match_data["enemy_team"])
                match_data["type"] = f"{our_count}vs{enemy_count}" if our_count and enemy_count else "Unknown"
                
                # 맵 설정 (기본값)
                match_data["map"] = "A보급창고"
                
                # 상대 클랜명 (추후 개선 가능)
                match_data["opponent"] = f"상대클랜{i+1}"
                
                # 매치 ID 중복 체크
                if match_data["match_id"] not in existing_ids and len(match_data["players"]) > 0:
                    all_matches.insert(0, match_data)
                    existing_ids.add(match_data["match_id"])
                    new_matches_count += 1
                    print(f"  ✅ 새 매치 추가됨 - {match_data['type']} {match_data['result']}")
                    print(f"     점수: {our_score}:{enemy_score}")
                    print(f"     참여: {[p['name'] for p in match_data['our_team']]}")
                else:
                    print("  ⏭️ 이미 존재하는 매치 또는 빈 매치")
                
                # 토글 닫기
                driver.execute_script("arguments[0].click();", toggles[i])
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ 매치 {i+1} 처리 중 오류: {str(e)}")
                # 토글 닫기 시도
                try:
                    toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
                    if i < len(toggles):
                        driver.execute_script("arguments[0].click();", toggles[i])
                except:
                    pass
                continue
        
        # 데이터 정렬 (최신순)
        all_matches.sort(key=lambda x: x.get('match_id', ''), reverse=True)
        
        # 최대 500개까지만 유지
        all_matches = all_matches[:500]
        
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
