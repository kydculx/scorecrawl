from typing import Optional
from utils.constants import LEAGUE_TABLE
from utils.supabase_client import get_supabase


def get_max_round(league_name: str, season_name: str) -> Optional[int]:
    """Supabase에서 특정 리그·시즌의 마지막 저장 라운드 조회

    Returns:
        int or None: 저장된 가장 큰 라운드 번호. 데이터가 없으면 None.
    """
    table_name = LEAGUE_TABLE.get(league_name)
    if not table_name:
        return None

    try:
        supabase = get_supabase()
        result = (
            supabase.table(table_name)
            .select("라운드")
            .eq("시즌", season_name)
            .order("라운드", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["라운드"]
        return None
    except Exception:
        return None


def get_max_round_by_table(table_name: str, season_name: str) -> Optional[int]:
    """테이블명을 직접 지정해서 마지막 저장 라운드 조회"""
    try:
        supabase = get_supabase()
        result = (
            supabase.table(table_name)
            .select("라운드")
            .eq("시즌", season_name)
            .order("라운드", desc=True)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["라운드"]
        return None
    except Exception:
        return None
