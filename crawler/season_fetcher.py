import re
import json
import gzip
import urllib.request


def extract_league_id(league_url: str) -> str:
    """URL에서 리그 ID 추출 (/league/36 → '36', /league/2025-2026/36 → '36')"""
    m = re.search(r'/league/(?:\d[^/]*/)?(\d+)', league_url)
    if m:
        return m.group(1)
    m = re.search(r'/(\d+)$', league_url)
    return m.group(1) if m else ""


def build_season_url(league_url: str, season_name: str, first_season: bool) -> str:
    """시즌명과 리그 URL로 시즌 페이지 경로 생성"""
    if first_season:
        return league_url
    lid = extract_league_id(league_url)
    return f"/league/{season_name}/{lid}"


def build_team_list_url(league_url: str, season_name: str) -> str:
    """시즌별 팀 목록 URL 추정"""
    lid = extract_league_id(league_url)
    return f"/leastanding/{season_name}/{lid}"


def fetch_seasons(league_url: str, domain: str = "scoreman123.com",
                  max_seasons: int = 10):
    """시즌 JSON API를 호출하여 시즌 목록 반환

    Returns:
        list of dict: [
            {"name": "2025-2026", "url": "/league/2025-2026/36",
             "team_list_url": "/leastanding/2025-2026/36"},
            ...
        ]
    """
    league_id = extract_league_id(league_url)
    if not league_id:
        return []

    api_url = f"https://football.{domain}/jsData/leagueSeason/sea{league_id}.json"
    try:
        req = urllib.request.Request(api_url, headers={"Accept-Encoding": "gzip"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            if resp.info().get("Content-Encoding") == "gzip":
                raw = gzip.decompress(raw)
            raw = raw.decode('utf-8-sig')
        data = json.loads(raw)
        seasons = data.get("SeasonList", [])

        result = []
        for i, s_name in enumerate(seasons[:max_seasons]):
            is_current = (i == 0)
            season_url = build_season_url(league_url, s_name, is_current)
            team_list_url = build_team_list_url(league_url, s_name)
            result.append({
                "name": s_name,
                "url": season_url,
                "team_list_url": team_list_url,
            })
        return result
    except Exception as e:
        print(f"[SeasonFetcher] Error fetching seasons: {e}")
        return []
