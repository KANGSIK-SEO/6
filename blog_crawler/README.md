# Tech Blog Crawler

실리콘밸리(구글·마이크로소프트·아마존·메타·애플 등)와 중국(메이투안·알리바바 클라우드·바이두 등)
주요 IT 기업 기술 블로그의 **최신 글**을 RSS/Atom 피드로 수집하는 크롤러입니다.

- 외부 의존성은 `requests` 하나뿐 (내장 XML 파서로 RSS 2.0 + Atom 모두 처리)
- 회사/지역/카테고리 필터, 최근 N일 필터, 피드별 개수 제한
- 콘솔 / JSON / Markdown 출력
- 피드를 동시에(멀티스레드) 수집하고, 실패한 피드는 건너뛰며 오류를 리포트

## 설치

```bash
pip install -r requirements.txt
```

## 사용법

```bash
# 최근 7일, 전체 회사, 콘솔 출력
python crawler.py

# 중국 기업만, 최근 14일
python crawler.py --region china --days 14

# 구글 관련 피드만, 피드당 5개, JSON 저장
python crawler.py --company google --limit 5 --format json --output articles.json

# 최근 3일치 Markdown 다이제스트
python crawler.py --days 3 --format markdown --output digest.md

# AI 카테고리만
python crawler.py --category ai

# 설정된 피드 목록 확인
python crawler.py --list-feeds
```

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--region {usa,china}` | 지역 필터 | 전체 |
| `--company TEXT` | 회사명 부분 일치 (예: `google`) | 전체 |
| `--category TEXT` | 카테고리 부분 일치 (`ai`, `cloud`, `engineering`, `general`) | 전체 |
| `--days N` | 최근 N일 이내 글만 (`0`이면 날짜 필터 없음) | `7` |
| `--limit N` | 피드당 최대 글 수 (`0`이면 무제한) | `0` |
| `--format {console,json,markdown}` | 출력 형식 | `console` |
| `--output FILE` | 파일로 저장 (미지정 시 표준출력) | 표준출력 |
| `--timeout SEC` | 요청 타임아웃(초) | `20` |
| `--workers N` | 동시 수집 스레드 수 | `8` |
| `--list-feeds` | 피드 목록만 출력하고 종료 | - |

## 네트워크 정책 관련 주의

이 저장소가 실행되는 Claude Code 웹/원격 환경은 **아웃바운드 네트워크 정책**에 따라
외부 호스트 접근이 제한될 수 있습니다. 예를 들어 `aws.amazon.com`, `tech.meituan.com`
같은 블로그 호스트가 허용 목록에 없으면 프록시가 `403`으로 CONNECT를 거부하여
실시간 수집이 되지 않습니다.

- 로컬 PC나 **네트워크 접근이 허용된 환경**에서 실행하면 그대로 동작합니다.
- 원격 환경에서 실행해야 한다면, 환경의 네트워크 정책을 완화하거나 필요한
  블로그 호스트를 허용 목록에 추가해야 합니다.
  (참고: https://code.claude.com/docs/en/claude-code-on-the-web)

## 피드 추가/수정

모든 피드는 [`feeds.py`](./feeds.py)의 `FEEDS` 리스트 한 곳에서 관리합니다.
새 회사를 추가하려면 다음 형식으로 항목을 넣으면 됩니다.

```python
{"company": "회사명", "region": "usa" 또는 "china",
 "category": "engineering|ai|cloud|general", "url": "RSS/Atom 피드 URL"},
```

> ByteDance(TikTok)·Tencent·Huawei 등 일부 중국 기업은 공개 블로그를 주로
> WeChat 공식계정으로 운영하여 안정적인 공개 RSS가 없습니다. 이런 소스는
> 별도 HTML 스크래퍼가 필요하며, `fetch_feed`와 동일한 반환 형식
> `(articles, error)`을 맞추면 크롤러에 그대로 연결할 수 있습니다.

## 구조

```
blog_crawler/
├── crawler.py       # 수집·파싱·필터·출력 + CLI
├── feeds.py         # 피드 카탈로그(단일 소스)
├── requirements.txt
└── README.md
```
