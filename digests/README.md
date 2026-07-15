# Digests

이 폴더에는 `Daily Tech Blog Digest` GitHub Actions 워크플로가 매일 생성하는
테크 기업 블로그 다이제스트가 쌓입니다.

- `YYYY-MM-DD.md` — 해당 날짜에 수집된 최신 글 목록
- `latest.md` — 가장 최근 다이제스트 사본

## 수동 실행

GitHub 저장소의 **Actions 탭 → Daily Tech Blog Digest → Run workflow** 에서
언제든 직접 실행할 수 있습니다. `days`(조회 기간), `region`(`usa`/`china`) 입력을
지정할 수 있습니다.

> 스케줄(cron) 트리거는 **기본 브랜치**에 워크플로가 병합된 뒤부터 동작합니다.
