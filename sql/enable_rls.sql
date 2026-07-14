-- 7개 리그 테이블 전체에 RLS를 활성화하고, 
-- 브라우저(공개 키)에서 조회(SELECT)가 가능하도록 읽기 권한 정책을 생성하는 쿼리입니다.
-- Supabase 대시보드 -> SQL Editor -> New Query에 복사하여 실행하세요.

-- 1. k_league_1
ALTER TABLE k_league_1 ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON k_league_1;
CREATE POLICY "Allow public read access" ON k_league_1 FOR SELECT USING (true);

-- 2. k_league_2
ALTER TABLE k_league_2 ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON k_league_2;
CREATE POLICY "Allow public read access" ON k_league_2 FOR SELECT USING (true);

-- 3. premier_league
ALTER TABLE premier_league ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON premier_league;
CREATE POLICY "Allow public read access" ON premier_league FOR SELECT USING (true);

-- 4. bundesliga
ALTER TABLE bundesliga ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON bundesliga;
CREATE POLICY "Allow public read access" ON bundesliga FOR SELECT USING (true);

-- 5. laliga
ALTER TABLE laliga ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON laliga;
CREATE POLICY "Allow public read access" ON laliga FOR SELECT USING (true);

-- 6. j1_league
ALTER TABLE j1_league ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON j1_league;
CREATE POLICY "Allow public read access" ON j1_league FOR SELECT USING (true);

-- 7. serie_a
ALTER TABLE serie_a ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow public read access" ON serie_a;
CREATE POLICY "Allow public read access" ON serie_a FOR SELECT USING (true);
