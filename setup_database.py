"""
Supabase 테이블 생성 스크립트
사용법: python setup_database.py
"""
import os
import sys

# .env 로드 (python-dotenv 없으면 직접 파싱)
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ .env 파일에 SUPABASE_URL과 SUPABASE_KEY가 필요합니다.")
    sys.exit(1)

# SQL 파일 읽기
sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "supabase", "migration.sql")
if not os.path.exists(sql_path):
    print(f"❌ migration.sql 파일 없음: {sql_path}")
    sys.exit(1)

with open(sql_path, "r", encoding="utf-8") as f:
    sql_content = f.read()

# CREATE TABLE 문만 추출
statements = []
current = []
for line in sql_content.split("\n"):
    if line.strip().upper().startswith("--"):
        continue
    current.append(line)
    if line.strip().endswith(";"):
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)
        current = []

print(f"📄 발견된 SQL 문: {len(statements)}개")

# pg-meta API로 SQL 실행
import httpx

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

# 엔드포인트 후보들
endpoints = [
    f"{SUPABASE_URL}/pg/sql/run",
    f"{SUPABASE_URL}/pg/sql",
    f"{SUPABASE_URL}/rest/v1/rpc/pg_sql",
]

success = False
api_url = None

for ep in endpoints:
    try:
        resp = httpx.post(
            ep,
            headers=headers,
            json={"query": statements[0]},
            timeout=10,
        )
        if resp.status_code in (200, 201):
            api_url = ep
            print(f"✅ pg-meta API 연결 성공: {ep}")
            success = True
            break
        elif resp.status_code == 404:
            print(f"  ↪ {ep} → 404 (시도 안 함)")
            continue
        else:
            print(f"  ↪ {ep} → {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"  ↪ {ep} → {e}")

if not success:
    print("\n⚠️  REST API로 SQL 실행이 안 됩니다. Supabase SQL Editor를 사용하세요.")
    print("   → https://supabase.com/dashboard/project/cjnzzbzlkfmapgjvsoxn/sql/new")
    print("   → supabase/migration.sql 파일 내용을 복사 → 붙여넣기 → Run\n")

    # supabase-py로 연결 테스트만
    try:
        from supabase import create_client
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        result = client.table("_dummy_test_").select("*").limit(1).execute()
        print(f"📡 supabase-py 연결: {'성공' if hasattr(result, 'data') else '실패'}")
    except Exception as e:
        print(f"📡 supabase-py 연결 테스트: {e}")
    
    print("\nSQL 파일 내용:")
    print(sql_content[:500] + "...")
    sys.exit(0)

# 모든 SQL 문 실행
for i, stmt in enumerate(statements):
    table_name = ""
    for line in stmt.split("\n"):
        if "create table" in line.lower():
            parts = line.split()
            for j, p in enumerate(parts):
                if p.lower() in ("table",) and j + 1 < len(parts):
                    table_name = parts[j + 1].strip()
                    break
            break

    print(f"  [{i+1}/{len(statements)}] {table_name} 생성 중...", end=" ")
    try:
        resp = httpx.post(
            api_url,
            headers=headers,
            json={"query": stmt},
            timeout=30,
        )
        if resp.status_code in (200, 201):
            print("✅")
        else:
            # "already exists"는 무시
            if "already exists" in resp.text.lower():
                print("⏩ (이미 존재)")
            else:
                print(f"❌ {resp.status_code} {resp.text[:120]}")
    except Exception as e:
        print(f"❌ {e}")

# 연결 확인
print("\n🔍 연결 확인 중...")
try:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    for table in ["k_league_1", "premier_league", "bundesliga", "laliga", "j1_league", "k_league_2", "serie_a"]:
        try:
            result = client.table(table).select("*").limit(1).execute()
            print(f"  ✅ {table}: 연결 성공")
        except Exception as e:
            print(f"  ❌ {table}: {e}")
except Exception as e:
    print(f"  ❌ supabase-py 연결 실패: {e}")

print("\n🎉 완료!")
