from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime
import pytz

def crawl_clan_matches():
    """평생 클랜 매치 크롤링 - Playwright 버전"""
    
    # 기존 데이터 로드
    try:
        with open('data.json', 'r', encoding='utf-8') as f:
            all_matches = json.load(f)
    except:
        all_matches = []
    
    # 이미 저장된 매치 ID
    existing_ids = {match.get('match_id') for match in all_matches if match.get('match_id')}
    
    print("🔍 평생 클랜 매치 크롤링 시작...")
    
    with sync_playwright() as p:
        # 브라우저 실행 (headless 모드)
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        
        # 새 페이지 생성
        page = browser.new_page(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        try:
            print("📄 평생 클랜 페이지 로딩 중...")
            page.goto("https://barracks.sa.nexon.com/clan/dasdsa1658/clanMatch", wait_until='networkidle')
            
            # 페이지 로딩 완료 대기
            print("⏳ 페이지 완전 로딩 대기...")
            page.wait_for_timeout(5000)  # 5초 대기
            
            print("📝 페이지 타이틀:", page.title())
            
            # 상세보기 버튼 찾기
            toggles = page.locator('.accordion-toggle').all()
            print(f"✅ {len(toggles)}개의 매치 발견!")
            
            if not toggles:
                print("❌ 매치를 찾을 수 없습니다.")
                # 디버그용 스크린샷
                page.screenshot(path="debug_screenshot.png")
                print("📸 디버그 스크린샷 저장됨")
                return
            
            # 한국 시간
            kst = pytz.timezone('Asia/Seoul')
            now = datetime.now(kst)
            
            new_matches_count = 0
            max_matches = min(20, len(toggles))  # 최대 20개 처리
            
            for i in range(max_matches):
                try:
                    print(f"\n🎮 매치 {i+1}/{max_matches} 처리 중...")
                    
                    # 매번 요소 다시 찾기 (DOM 변경 대응)
                    toggle = page.locator('.accordion-toggle').nth(i)
                    
                    # 상세보기 클릭
                    toggle.scroll_into_view_if_needed()
                    toggle.click()
                    page.wait_for_timeout(1500)  # 1.5초 대기
                    
                    # 매치 상세 정보 파싱
                    match_data = parse_match_details(page, i, now)
                    
                    if match_data and match_data['match_id'] not in existing_ids:
                        all_matches.insert(0, match_data)
                        existing_ids.add(match_data['match_id'])
                        new_matches_count += 1
                        
                        print(f"  ✅ 새 매치 추가됨")
                        print(f"     결과: {match_data['result']}")
                        print(f"     점수: {match_data['score']['our']}:{match_data['score']['enemy']}")
                        print(f"     참여: {[p['name'] for p in match_data['our_team']]}")
                    
                    # 토글 닫기
                    toggle.click()
                    page.wait_for_timeout(500)
                    
                except Exception as e:
                    print(f"  ❌ 매치 {i+1} 처리 중 오류: {str(e)}")
                    continue
            
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
            browser.close()

def parse_match_details(page, match_index, now):
    """매치 상세 정보 파싱"""
    try:
        # 현재 펼쳐진 매치 상세 정보 찾기
        # 토글 다음에 나타나는 상세 정보 tbody 찾기
        detail_selector = f'.accordion-toggle:nth-child({match_index + 1}) ~ tr tbody, .match-detail tbody'
        
        # 여러 방법으로 시도
        tbody = None
        
        # 방법 1: 직접 선택
        if page.locator(detail_selector).count() > 0:
            tbody = page.locator(detail_selector).first
        
        # 방법 2: 모든 tbody 중에서 찾기
        if not tbody:
            all_tbody = page.locator('tbody').all()
            for tb in all_tbody:
                # 보이고 있고, 충분한 행이 있는 tbody 찾기
                if tb.is_visible() and tb.locator('tr').count() > 3:
                    tbody = tb
                    break
        
        if not tbody:
            print("  ⚠️ 매치 상세 정보를 찾을 수 없음")
            return None
        
        # 매치 데이터 초기화
        match_data = {
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M"),
            "match_id": f"match_{now.strftime('%Y%m%d')}_{match_index}_{int(time.time())}",
            "our_team": [],
            "enemy_team": [],
            "players": [],
            "map": "A보급창고"
        }
        
        # 모든 행 가져오기
        rows = tbody.locator('tr').all()
        current_team = None
        our_score = 0
        enemy_score = 0
        
        for row in rows:
            cells = row.locator('td').all()
            if not cells:
                continue
            
            first_cell_text = cells[0].text_content().strip()
            
            # 팀 구분
            if first_cell_text in ["승리", "승"]:
                current_team = "our"
                match_data["result"] = "win"
                continue
            elif first_cell_text in ["패배", "패"]:
                current_team = "our"
                match_data["result"] = "lose"
                continue
            elif first_cell_text in ["gear", "적팀", "상대팀", "enemy"]:
                current_team = "enemy"
                continue
            
            # 팀 합산 기록
            if "팀 합산" in first_cell_text or "합산" in first_cell_text:
                if len(cells) >= 2 and current_team:
                    try:
                        score = int(cells[1].text_content().strip())
                        if current_team == "our":
                            our_score = score
                        else:
                            enemy_score = score
                    except:
                        pass
                continue
            
            # 플레이어 데이터 파싱
            if len(cells) >= 7 and current_team:
                try:
                    # 닉네임이 비어있거나 특수한 경우 스킵
                    player_name = cells[0].text_content().strip()
                    if not player_name or player_name in ["승리", "패배", "팀 합산 기록"]:
                        continue
                    
                    player_data = {
                        "name": player_name,
                        "kills": int(cells[1].text_content().strip() or 0),
                        "deaths": int(cells[2].text_content().strip() or 0),
                        "headshots": int(cells[3].text_content().strip() or 0),
                        "assists": int(cells[4].text_content().strip() or 0),
                        "saves": int(cells[5].text_content().strip() or 0),
                        "damage": int(cells[6].text_content().strip().replace(",", "") or 0),
                        "team": current_team
                    }
                    
                    match_data["players"].append(player_data)
                    
                    if current_team == "our":
                        match_data["our_team"].append(player_data)
                    else:
                        match_data["enemy_team"].append(player_data)
                        
                except Exception as e:
                    print(f"    플레이어 데이터 파싱 오류: {e}")
                    continue
        
        # 점수 설정
        match_data["score"] = {"our": our_score, "enemy": enemy_score}
        
        # 매치 타입 설정
        our_count = len(match_data["our_team"])
        enemy_count = len(match_data["enemy_team"])
        match_data["type"] = f"{our_count}vs{enemy_count}" if our_count and enemy_count else "Unknown"
        
        # 상대 클랜명 (나중에 개선 가능)
        match_data["opponent"] = f"상대클랜"
        
        return match_data if len(match_data["players"]) > 0 else None
        
    except Exception as e:
        print(f"  ❌ 매치 상세 파싱 오류: {str(e)}")
        return None

if __name__ == "__main__":
    crawl_clan_matches()
