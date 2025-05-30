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

def crawl_clan_matches():
    # Chrome 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # 드라이버 자동 설치
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        print("🔍 크롤링 시작...")
        driver.get("https://barracks.sa.nexon.com/clan/dasdsa1658/clanMatch")
        
        # 페이지 로딩 대기
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "accordion-toggle")))
        time.sleep(3)
        
        # 기존 데이터 로드
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                all_matches = json.load(f)
        except:
            all_matches = []
        
        # 이미 저장된 매치 ID 집합
        existing_ids = {match.get('match_id') for match in all_matches if match.get('match_id')}
        
        # 상세보기 버튼들 찾기
        toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
        print(f"📊 발견된 매치 수: {len(toggles)}개")
        
        new_matches = []
        
        # 최대 20개까지만 처리 (최신 매치 위주)
        max_matches = min(20, len(toggles))
        
        for i in range(max_matches):
            try:
                # 매번 요소를 다시 찾기 (DOM 변경 대응)
                toggles = driver.find_elements(By.CLASS_NAME, "accordion-toggle")
                if i >= len(toggles):
                    break
                    
                print(f"🎮 매치 {i+1}/{max_matches} 처리 중...")
                
                # 토글 클릭
                driver.execute_script("arguments[0].scrollIntoView(true);", toggles[i])
                time.sleep(0.5)
                toggles[i].click()
                time.sleep(1)
                
                # 매치 데이터 추출
                match_data = extract_match_data(driver, i)
                
                if match_data and match_data.get('match_id') not in existing_ids:
                    new_matches.append(match_data)
                    print(f"✅ 새 매치 발견: {match_data['date']} {match_data['time']}")
                
                # 토글 닫기
                toggles[i].click()
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️  매치 {i+1} 처리 중 오류: {e}")
                continue
        
        # 새 매치를 기존 데이터 앞에 추가 (최신순)
        all_matches = new_matches + all_matches
        
        # 최대 500개까지만 저장 (파일 크기 관리)
        all_matches = all_matches[:500]
        
        # 데이터 저장
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(all_matches, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 크롤링 완료! 총 {len(all_matches)}개 매치 저장됨")
        print(f"🆕 새로 추가된 매치: {len(new_matches)}개")
        
    finally:
        driver.quit()

def extract_match_data(driver, match_index):
    """매치 데이터 추출"""
    try:
        # 현재 시간 (한국 시간)
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst)
        
        # 매치 정보가 있는 tbody 찾기
        # accordion-toggle 다음에 오는 tr 안의 tbody를 찾아야 함
        match_tbody = driver.find_elements(By.CSS_SELECTOR, "tr[style*='display'] tbody")[match_index]
        rows = match_tbody.find_elements(By.TAG_NAME, "tr")
        
        if len(rows) < 3:  # 최소한 헤더 + 플레이어 + 합계 행이 있어야 함
            return None
        
        # 매치 결과 및 플레이어 데이터 파싱
        match_data = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "match_id": f"{now.strftime('%Y%m%d%H%M')}_{match_index}",
            "players": [],
            "our_team": [],
            "enemy_team": []
        }
        
        current_team = None
        our_score = 0
        enemy_score = 0
        
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            
            if len(cells) == 0:
                continue
                
            first_cell_text = cells[0].text.strip()
            
            # 팀 구분
            if first_cell_text == "승리" or first_cell_text == "승":
                current_team = "our"
                match_data["result"] = "win"
                continue
            elif first_cell_text == "패배" or first_cell_text == "패":
                current_team = "our"
                match_data["result"] = "lose"
                continue
            elif first_cell_text in ["gear", "적팀", "상대"]:
                current_team = "enemy"
                continue
            
            # 팀 합산 기록
            if "팀 합산" in first_cell_text or "합산" in first_cell_text:
                if len(cells) >= 3:
                    try:
                        if current_team == "our":
                            our_score = int(cells[1].text)
                        else:
                            enemy_score = int(cells[1].text)
                    except:
                        pass
                continue
            
            # 플레이어 데이터
            if len(cells) >= 8 and current_team:
                try:
                    player_data = {
                        "name": cells[0].text.strip(),
                        "kills": int(cells[1].text),
                        "deaths": int(cells[2].text),
                        "headshots": int(cells[3].text),
                        "assists": int(cells[4].text),
                        "saves": int(cells[5].text),
                        "damage": int(cells[6].text.replace(",", "")),
                        "team": current_team
                    }
                    
                    # 전체 플레이어 리스트에 추가
                    match_data["players"].append(player_data)
                    
                    # 팀별 리스트에도 추가
                    if current_team == "our":
                        match_data["our_team"].append(player_data)
                    else:
                        match_data["enemy_team"].append(player_data)
                        
                except Exception as e:
                    print(f"플레이어 데이터 파싱 오류: {e}")
                    continue
        
        # 점수 설정
        match_data["score"] = {
            "our": our_score,
            "enemy": enemy_score
        }
        
        # 매치 타입 결정 (플레이어 수 기반)
        our_count = len(match_data["our_team"])
        enemy_count = len(match_data["enemy_team"])
        match_data["type"] = f"{our_count}vs{enemy_count}"
        
        # 맵 정보 (기본값)
        match_data["map"] = "A보급창고"
        
        # 상대 클랜명 추출 시도
        try:
            # 매치 정보 행에서 상대 클랜명 찾기
            info_rows = driver.find_elements(By.CSS_SELECTOR, ".match-info")
            if info_rows and match_index < len(info_rows):
                match_data["opponent"] = info_rows[match_index].text.split()[0]
            else:
                match_data["opponent"] = "Unknown"
        except:
            match_data["opponent"] = "Unknown"
        
        return match_data if len(match_data["players"]) > 0 else None
        
    except Exception as e:
        print(f"❌ 데이터 추출 오류: {e}")
        return None

if __name__ == "__main__":
    crawl_clan_matches()
