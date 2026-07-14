-- 기존 unique 제약조건 변경
-- (시즌, 라운드, 홈, 원정) → (시즌, 날짜, 시간, 홈, 원정)
-- 이미 migration.sql을 실행한 경우에만 필요

alter table k_league_1 drop constraint if exists k_league_1_시즌_라운드_홈_원정_key;
alter table k_league_1 add constraint k_league_1_unique unique(시즌, 날짜, 시간, 홈, 원정);

alter table k_league_2 drop constraint if exists k_league_2_시즌_라운드_홈_원정_key;
alter table k_league_2 add constraint k_league_2_unique unique(시즌, 날짜, 시간, 홈, 원정);

alter table premier_league drop constraint if exists premier_league_시즌_라운드_홈_원정_key;
alter table premier_league add constraint premier_league_unique unique(시즌, 날짜, 시간, 홈, 원정);

alter table bundesliga drop constraint if exists bundesliga_시즌_라운드_홈_원정_key;
alter table bundesliga add constraint bundesliga_unique unique(시즌, 날짜, 시간, 홈, 원정);

alter table laliga drop constraint if exists laliga_시즌_라운드_홈_원정_key;
alter table laliga add constraint laliga_unique unique(시즌, 날짜, 시간, 홈, 원정);

alter table j1_league drop constraint if exists j1_league_시즌_라운드_홈_원정_key;
alter table j1_league add constraint j1_league_unique unique(시즌, 날짜, 시간, 홈, 원정);

alter table serie_a drop constraint if exists serie_a_시즌_라운드_홈_원정_key;
alter table serie_a add constraint serie_a_unique unique(시즌, 날짜, 시간, 홈, 원정);
