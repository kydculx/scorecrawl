import re
import json
import pandas as pd
import os
from utils.constants import STATS_COLUMNS, PLAYER_STATS_HEADER
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side

class DataProcessor:
    @staticmethod
    def clean_team_name(text):
        """팀 이름 정제"""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\[[^\]]*\]', '', text)
        text = re.sub(r'^\d+\s*', '', text)
        text = re.sub(r'\s*\d+$', '', text)
        return text.strip()

    @staticmethod
    def parse_team_rank(text):
        """팀 이름과 순위 분리"""
        text = re.sub(r'<[^>]+>', '', text)
        bracket_match = re.search(r'\[([^\]]+)\]', text)
        rank = "-"
        
        if bracket_match:
            bracket_content = bracket_match.group(1).strip()
            if bracket_content.isdigit():
                rank = bracket_content
        
        cleaned_text = re.sub(r'\[[^\]]*\]', '', text)
        cleaned_text = re.sub(r'^\d+\s*', '', cleaned_text)
        cleaned_text = re.sub(r'\s*\d+$', '', cleaned_text)
        return cleaned_text.strip(), rank

    @staticmethod
    def safe_get_value(val):
        """값 안전하게 추출"""
        try:
            if isinstance(val, pd.Series):
                val = val.iloc[0] if not val.empty else None
            if val is None:
                return None
            if isinstance(val, float) and (val != val):  # NaN check
                return None
            return val
        except (ValueError, TypeError, AttributeError):
            return None

    @staticmethod
    def safe_excel_value(val):
        """엑셀 저장용 값 변환"""
        if val is None: return ""
        try:
            if isinstance(val, float) and (val != val): return ""
        except: pass
        if val == "": return ""
        if isinstance(val, (int, float)): return str(val)
        try:
            return ''.join(char for char in str(val).strip() if ord(char) >= 32 or char in '\n\r\t')
        except: return ""

    @classmethod
    def save_results(cls, df, title, ordered_companies, log_callback=None, league_name=None, season_name=None):
        if df.empty:
            if log_callback: log_callback("데이터가 없습니다.")
            return None

        safe_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        filename = f"{safe_title}.xlsx"
        json_filename = f"{safe_title}.json"

        if log_callback: log_callback("\n[데이터 변환 및 저장 중...]")

        # 1. 데이터 프레임 전처리 (피벗)
        index_cols = ["Round", "날짜", "시간", "홈", "홈순위", "스코어", "원정", "원정순위"]
        df_unique = df.drop_duplicates(subset=index_cols + ["Company"])
        pivot_df = df_unique.pivot(index=index_cols, columns="Company", values=["승", "무", "패"])
        pivot_df = pivot_df.swaplevel(0, 1, axis=1)
        
        # 컬럼 정렬
        sorted_cols = []
        for comp in ordered_companies:
            for type_ in ["승", "무", "패"]:
                if (comp, type_) in pivot_df.columns:
                    sorted_cols.append((comp, type_))
        pivot_df = pivot_df.reindex(columns=sorted_cols)
        pivot_df.reset_index(inplace=True)

        # 행 정렬
        pivot_df['_라운드_정렬'] = pd.to_numeric(pivot_df['Round'], errors='coerce')
        pivot_df['_날짜_정렬'] = pivot_df['날짜'].apply(
            lambda x: pd.to_datetime(x, format='%m.%d', errors='coerce') if pd.notna(x) else pd.NaT
        )
        pivot_df = pivot_df.sort_values(by=['_라운드_정렬', '_날짜_정렬', '시간'], na_position='last')
        pivot_df.drop(columns=['_라운드_정렬', '_날짜_정렬'], inplace=True)
        pivot_df.reset_index(drop=True, inplace=True)
        pivot_df.index.name = "순서"

        if log_callback: log_callback(f"[결과] 총 {len(pivot_df)}개의 경기 데이터 처리")

        # 2. JSON 데이터 생성 (Excel 생성용)
        json_data = cls._create_json_data(pivot_df, index_cols, league_name, season_name)

        # 3. Excel 생성
        # 실제 데이터에 존재하는 회사 목록 업데이트
        companies_in_data = set()
        for match in json_data:
            for comp in match.get("Odds", {}).keys():
                companies_in_data.add(comp)
        
        final_companies = [c for c in ordered_companies if c in companies_in_data]
        for c in companies_in_data:
            if c not in final_companies:
                final_companies.append(c)

        # AVERAGE를 맨 앞으로 이동
        if "AVERAGE" in final_companies:
            final_companies.remove("AVERAGE")
            final_companies.insert(0, "AVERAGE")

        cls._create_excel(json_data, filename, final_companies)
        if log_callback: log_callback(f"엑셀 저장 완료: {filename}")

        return filename

    @classmethod
    def save_team_results(cls, result_data, team_name, log_callback=None):
        """팀 데이터 저장 (엑셀 단일 시트)"""
        if not result_data or (not isinstance(result_data, dict) and result_data.empty):
            if log_callback: log_callback("저장할 팀 데이터가 없습니다.")
            return None
            
        safe_name = re.sub(r'[\\/*?:"<>|]', "", team_name).strip()
        filename = f"{safe_name}_팀정보.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                # 1. 통계 데이터 저장 (정의된 순서대로 하나의 시트에)
                stats_data = result_data.get("stats", {})
                
                # 스타일 정의
                header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid") # 남색 배경
                header_font = Font(color="FFFFFF", bold=True) # 흰색 글씨
                center_align = Alignment(horizontal='center', vertical='center')
                thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                                   top=Side(style='thin'), bottom=Side(style='thin'))

                sheet_name = "팀정보"
                start_row = 1
                
                # 빈 시트 생성 (데이터가 하나라도 있을 때)
                if stats_data:
                    writer.book.create_sheet(sheet_name)
                    ws = writer.book[sheet_name]
                    # 기본 시트 제거 (Sheet)
                    if 'Sheet' in writer.book.sheetnames:
                        del writer.book['Sheet']

                    for key, columns in STATS_COLUMNS.items():
                        if key in stats_data:
                            df = stats_data[key]
                            
                            # 제목 추가
                            ws.cell(row=start_row, column=1, value=key).font = Font(bold=True, size=12)
                            start_row += 1

                            # 데이터 프레임 쓰기
                            # to_excel은 startrow 인자를 받지만 openpyxl writer 객체에서는 직접 제어하는게 나음
                            # 하지만 pandas의 to_excel 기능을 활용하기 위해 writer를 사용하되, 
                            # 기존 시트에 덮어쓰지 않고 위치를 지정해야 함.
                            
                            # pandas to_excel 사용 시 startrow 옵션 활용
                            df.to_excel(writer, sheet_name=sheet_name, startrow=start_row-1, index=False)
                            
                            # 스타일 적용 (방금 추가한 영역에 대해)
                            # 헤더 (start_row)
                            for col_idx, col_name in enumerate(df.columns, 1):
                                cell = ws.cell(row=start_row, column=col_idx)
                                cell.fill = header_fill
                                cell.font = header_font
                                cell.alignment = center_align
                                cell.border = thin_border
                                
                            # 데이터
                            for r_idx in range(len(df)):
                                current_row = start_row + 1 + r_idx
                                for c_idx in range(len(df.columns)):
                                    cell = ws.cell(row=current_row, column=c_idx+1)
                                    cell.alignment = center_align
                                    cell.border = thin_border
                            
                            # 다음 테이블을 위한 공백
                            start_row += len(df) + 3 # 데이터 행 수 + 헤더 + 빈 줄 2개

                    # 2. 선수 정보 저장 (players 키가 있는 경우)
                    players = result_data.get("players")
                    if players:
                        # 선수 리스트를 DataFrame으로 변환
                        # summary_stats만 추출
                        player_rows = []
                        for p in players:
                            if "summary_stats" in p:
                                player_rows.append(p["summary_stats"])
                        
                        if player_rows:
                            df_players = pd.DataFrame(player_rows)
                            # 컬럼 정렬 (PLAYER_STATS_HEADER 기준)
                            cols = [c for c in PLAYER_STATS_HEADER if c in df_players.columns]
                            if cols:
                                df_players = df_players[cols]
                            
                            # 제목 추가
                            ws.cell(row=start_row, column=1, value="선수 목록").font = Font(bold=True, size=12)
                            start_row += 1

                            # 데이터 프레임 쓰기
                            df_players.to_excel(writer, sheet_name=sheet_name, startrow=start_row-1, index=False)
                            
                            # 스타일 적용
                            # 헤더
                            for col_idx, col_name in enumerate(df_players.columns, 1):
                                cell = ws.cell(row=start_row, column=col_idx)
                                cell.fill = header_fill
                                cell.font = header_font
                                cell.alignment = center_align
                                cell.border = thin_border
                                
                            # 데이터
                            for r_idx in range(len(df_players)):
                                current_row = start_row + 1 + r_idx
                                for c_idx in range(len(df_players.columns)):
                                    cell = ws.cell(row=current_row, column=c_idx+1)
                                    cell.alignment = center_align
                                    cell.border = thin_border
                            
                            start_row += len(df_players) + 3

                    # 컬럼 너비 자동 조정 (전체 시트 처리)
                    for col in ws.columns:
                        max_length = 0
                        column = col[0].column_letter
                        for cell in col:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        ws.column_dimensions[column].width = adjusted_width

            if log_callback: log_callback(f"엑셀 저장 완료: {filename}")
            return filename
        except Exception as e:
            if log_callback: log_callback(f"엑셀 저장 실패: {e}")
            return None

    @classmethod
    def save_player_results(cls, result_data, player_name, log_callback=None):
        """선수 데이터 저장 (엑셀 단일 시트)"""
        if not result_data or (not isinstance(result_data, dict) and result_data.empty):
            if log_callback: log_callback("저장할 선수 데이터가 없습니다.")
            return None
            
        safe_name = re.sub(r'[\\/*?:"<>|]', "", player_name).strip()
        filename = f"{safe_name}_선수정보.xlsx"
        
        try:
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                stats_data = result_data.get("stats", {})
                
                # 스타일 정의
                header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
                header_font = Font(color="FFFFFF", bold=True)
                center_align = Alignment(horizontal='center', vertical='center')
                thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), 
                                   top=Side(style='thin'), bottom=Side(style='thin'))

                sheet_name = "선수정보"
                start_row = 1
                
                if stats_data:
                    writer.book.create_sheet(sheet_name)
                    ws = writer.book[sheet_name]
                    if 'Sheet' in writer.book.sheetnames:
                        del writer.book['Sheet']

                    for key, df in stats_data.items():
                        # 제목
                        ws.cell(row=start_row, column=1, value=key).font = Font(bold=True, size=12)
                        start_row += 1

                        df.to_excel(writer, sheet_name=sheet_name, startrow=start_row-1, index=False)
                        
                        # 스타일 적용
                        # 헤더
                        for col_idx, col_name in enumerate(df.columns, 1):
                            cell = ws.cell(row=start_row, column=col_idx)
                            cell.fill = header_fill
                            cell.font = header_font
                            cell.alignment = center_align
                            cell.border = thin_border
                            
                        # 데이터
                        for r_idx in range(len(df)):
                            current_row = start_row + 1 + r_idx
                            for c_idx in range(len(df.columns)):
                                cell = ws.cell(row=current_row, column=c_idx+1)
                                cell.alignment = center_align
                                cell.border = thin_border
                        
                        start_row += len(df) + 3

                    # 컬럼 너비 조정
                    for col in ws.columns:
                        max_length = 0
                        column = col[0].column_letter
                        for cell in col:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = (max_length + 2)
                        ws.column_dimensions[column].width = adjusted_width

            if log_callback: log_callback(f"엑셀 저장 완료: {filename}")
            return filename
        except Exception as e:
            if log_callback: log_callback(f"엑셀 저장 실패: {e}")
            return None

    @classmethod
    def _create_json_data(cls, df, match_info_cols, league_name=None, season_name=None):
        json_data = []
        for _, row in df.iterrows():
            match_data = {
                "League": league_name,
                "Season": season_name
            }
            
            # 기본 정보
            if "Round" in df.columns: match_data["Round"] = cls.safe_get_value(row["Round"])
            
            date_val = cls.safe_get_value(row["날짜"]) if "날짜" in df.columns else None
            time_val = cls.safe_get_value(row["시간"]) if "시간" in df.columns else None
            if date_val or time_val:
                match_data["DateTime"] = {"Date": date_val, "Time": time_val}

            # 팀 정보
            for side, eng_side in [("홈", "Home"), ("원정", "Away")]:
                team = cls.safe_get_value(row[side]) if side in df.columns else None
                rank = cls.safe_get_value(row[f"{side}순위"]) if f"{side}순위" in df.columns else None
                if team or rank:
                    match_data[eng_side] = {"Team": team, "Rank": rank}

            # 스코어
            score = cls.safe_get_value(row["스코어"]) if "스코어" in df.columns else "-"
            score = str(score).strip() if score else "-"
            home_score, away_score = "-", "-"
            
            # 구분자 (:, -)를 기준으로 숫자 추출
            import re
            score_match = re.search(r'(\d+)\s*[:\-]\s*(\d+)', score)
            if score_match:
                home_score, away_score = score_match.group(1), score_match.group(2)
                match_data["Score"] = f"{home_score}-{away_score}"
            else:
                 match_data["Score"] = score
            match_data["HomeScore"] = home_score
            match_data["AwayScore"] = away_score

            # 배당 정보
            odds_data = {}
            
            # 평균 계산을 위한 누적 변수
            win_sum, win_cnt = 0.0, 0
            draw_sum, draw_cnt = 0.0, 0
            loss_sum, loss_cnt = 0.0, 0

            for col in df.columns:
                if isinstance(col, tuple) and len(col) == 2:
                    comp, type_ = col
                    if comp not in match_info_cols and type_ in ["승", "무", "패"]:
                        val = cls.safe_get_value(row[col])
                        
                        # Try to convert to float for averaging
                        float_val = None
                        try:
                            if val is not None and val != "":
                                float_val = float(val)
                        except (ValueError, TypeError):
                            float_val = None

                        if isinstance(float_val, (int, float)):
                            if type_ == "승":
                                win_sum += float_val
                                win_cnt += 1
                            elif type_ == "무":
                                draw_sum += float_val
                                draw_cnt += 1
                            elif type_ == "패":
                                loss_sum += float_val
                                loss_cnt += 1

                        if comp not in odds_data: odds_data[comp] = {}
                        eng_type = {"승": "W", "무": "D", "패": "L"}.get(type_, type_)
                        odds_data[comp][eng_type] = val
            
            # 평균 배당 추가
            # AVERAGE 배당 추가
            if win_cnt > 0 or draw_cnt > 0 or loss_cnt > 0:
                avg_win = round(win_sum / win_cnt, 2) if win_cnt > 0 else None
                avg_draw = round(draw_sum / draw_cnt, 2) if draw_cnt > 0 else None
                avg_loss = round(loss_sum / loss_cnt, 2) if loss_cnt > 0 else None
                
                if "AVERAGE" not in odds_data: odds_data["AVERAGE"] = {}
                odds_data["AVERAGE"] = {"W": avg_win, "D": avg_draw, "L": avg_loss}
            
            if odds_data: match_data["Odds"] = odds_data
            
            # 유효성 검사 (팀 정보 없음 제외)
            if not match_data.get("Home", {}).get("Team") and not match_data.get("Away", {}).get("Team"):
                continue
                
            json_data.append(match_data)
        return json_data

    @classmethod
    def _create_excel(cls, json_data, filename, companies):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font
            
            wb = Workbook()
            ws = wb.active
            
            # 스타일
            align_center = Alignment(horizontal='center', vertical='center')
            font_bold = Font(bold=True)
            
            # 헤더 구성 (단일 행)
            header_row = ["LEAGUE", "SEASON", "ROUND", "DATE", "TIME", 
                          "HOME_TEAM", "HOME_RANK", "HOME_SCORE", "AWAY_SCORE", 
                          "AWAY_TEAM", "AWAY_RANK"]
            
            for comp in companies:
                header_row.extend([f"{comp}_W", f"{comp}_D", f"{comp}_L"])

            ws.append(header_row)

            # 헤더 스타일
            for cell in ws[1]:
                cell.alignment = align_center
                cell.font = font_bold
            
            # 병합 로직 제거 (한줄 헤더)
            
            # 데이터 채우기
            for match in json_data:
                row = []
                row.append(cls.safe_excel_value(match.get("League")))
                row.append(cls.safe_excel_value(match.get("Season")))
                row.append(cls.safe_excel_value(match.get("Round")))
                
                dt = match.get("DateTime", {})
                row.extend([cls.safe_excel_value(dt.get("Date")), cls.safe_excel_value(dt.get("Time"))])
                
                home = match.get("Home", {})
                row.extend([cls.safe_excel_value(home.get("Team")), cls.safe_excel_value(home.get("Rank"))])
                
                row.extend([cls.safe_excel_value(match.get("HomeScore")), cls.safe_excel_value(match.get("AwayScore"))])
                
                away = match.get("Away", {})
                row.extend([cls.safe_excel_value(away.get("Team")), cls.safe_excel_value(away.get("Rank"))])
                
                odds = match.get("Odds", {})
                for comp in companies:
                    c_odds = odds.get(comp, {})
                    row.extend([
                        cls.safe_excel_value(c_odds.get("W")),
                        cls.safe_excel_value(c_odds.get("D")),
                        cls.safe_excel_value(c_odds.get("L"))
                    ])
                ws.append(row)

            # 전체 데이터 정렬
            for row in ws.iter_rows(min_row=3, max_row=ws.max_row):
                for cell in row:
                    cell.alignment = align_center

            wb.save(filename)
            
        except Exception as e:
            raise Exception(f"Excel 생성 실패: {str(e)}")
