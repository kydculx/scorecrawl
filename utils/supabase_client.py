import os
from typing import Optional
from supabase import create_client, Client

_client: Optional[Client] = None


def _load_env():
    """.env 파일이 있으면 환경변수로 로드 (python-dotenv 없이)"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip())


def get_supabase() -> Client:
    global _client
    if _client is None:
        _load_env()
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise RuntimeError(
                "SUPABASE_URL과 SUPABASE_KEY를 .env 파일에 설정해야 합니다."
            )
        _client = create_client(url, key)
    return _client


def reset_client():
    global _client
    _client = None
