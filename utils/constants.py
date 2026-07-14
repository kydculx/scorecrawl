LEAGUE_DATA = [
    {"name": "K리그 1", "url": "/league/15"},
    {"name": "K리그 2", "url": "/league/1292"},
    {"name": "프리미어리그", "url": "/league/36"},
    {"name": "분데스리가", "url": "/league/8"},
    {"name": "라리가", "url": "/league/31"},
    {"name": "J1리그", "url": "/league/25"},
    {"name": "세리에 A", "url": "/league/34"},
]

# Supabase 테이블명 매핑 (리그명 → 테이블명)
LEAGUE_TABLE = {
    "K리그 1": "k_league_1",
    "K리그 2": "k_league_2",
    "프리미어리그": "premier_league",
    "분데스리가": "bundesliga",
    "라리가": "laliga",
    "J1리그": "j1_league",
    "세리에 A": "serie_a",
}
