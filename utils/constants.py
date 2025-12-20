# 리그 경로 정보 (도메인 제외)
# (표시 이름, 리그 URL, 팀 목록 URL)
LEAGUE_PATHS = [
    ("리그 선택", "", ""),
    ("K리그 1", "/subleague/15", "/subleastanding/2025/15/313"),
    ("프리미어리그", "/league/36", "/leastanding/36"),
]

# 엑셀 저장을 위한 컬럼 정의 (팀)
STATS_COLUMNS = {
    "리그_승점": ["경기", "승", "무승부", "패", "골인", "실점", "득실차", "승%", "무승부%", "패%", "평균 골인", "평균 실점", "승점"],
    "전반전_리그_승점": ["경기", "승", "무승부", "패", "골인", "실점", "득실차", "승%", "무승부%", "패%", "평균 골인", "평균 실점", "승점"],
    "핸디캡_순위": ["경기", "주기", "핸무", "받기", "승", "무승부", "패", "득실차", "승%", "무승부%", "패%", "랭킹"],
    "전반_핸디캡": ["경기", "주기", "핸무", "받기", "승", "무승부", "패", "득실차", "승%", "무승부%", "패%", "랭킹"],
    "오버_순위": ["경기", "오버", "무승부", "언더", "오버%", "무승부%", "언더%", "랭킹"],
    "전반_오버_언더": ["경기", "오버", "무승부", "언더", "오버%", "무승부%", "언더%", "랭킹"],
}

# 선수 정보 컬럼 (이미지 기반)
PLAYER_STATS_HEADER = ["랭킹", "선수", "국가", "골인", "골인/승", "골인/무", "골인/패", "옐로카드", "레드카드"]

# 팀별 선수 정보 URL (팀 이름: URL)
TEAM_PLAYER_URLS = {
    # K리그 1
    "전북현대": "/team/playerdata/484",
    "김천상무": "/team/playerdata/494",
    "대전FC": "/team/playerdata/488",
    "포항": "/team/playerdata/481",
    "FC 서울": "/team/playerdata/741",
    "강원FC": "/team/playerdata/9945",
    "안양FC": "/team/playerdata/21249",
    "광주FC": "/team/playerdata/16584",
    "울산 HD": "/team/playerdata/480",
    "수원FC": "/team/playerdata/5586",
    "제주SK": "/team/playerdata/4075",
    "대구FC": "/team/playerdata/491",

    # 프리미어리그
    "아스널": "/team/playerdata/19",
    "맨체스터 시티": "/team/playerdata/26",
    "아스톤 빌라": "/team/playerdata/20",
    "첼시": "/team/playerdata/24",
    "크리스탈팰리스": "/team/playerdata/35",
    "맨체스터 유나이티드": "/team/playerdata/27",
    "리버풀": "/team/playerdata/25",
    "선덜랜드": "/team/playerdata/65",
    "에버턴": "/team/playerdata/31",
    "브라이튼": "/team/playerdata/60",
    "뉴캐슬 Utd": "/team/playerdata/28",
    "토트넘": "/team/playerdata/33",
    "본머스": "/team/playerdata/348",
    "풀럼": "/team/playerdata/29",
    "브렌트퍼드": "/team/playerdata/365",
    "노팅엄": "/team/playerdata/49",
    "리즈": "/team/playerdata/56",
    "웨스트햄": "/team/playerdata/62",
    "번리": "/team/playerdata/48",
    "울버햄튼": "/team/playerdata/52",
}
