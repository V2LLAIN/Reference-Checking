# BibTeX Reference Auditor — Semantic Scholar 전용

Google Scholar 수동 비교판(`bibtex_auditor_manual_review/enhance_report.py`)과 **완전히 별도로** 사용하는 Semantic Scholar API 버전입니다. Google Scholar API를 사용하는 것이 아닙니다.

기존의 `check_bib.py`, `enhance_report.py`, `main.bib`, `audit_results/report.csv`, `audit_results/report_review.html`은 수정하지 않습니다.

## 설치

`semantic_scholar_report.py`를 **기존 프로젝트의 루트** (`check_bib.py` 옆)에 놓거나 `semantic_scholar_auditor/` 하위에 놓습니다.

```text
bib-reference-auditor/
├── check_bib.py                      # 기존
├── main.bib                          # 기존
├── bibtex_auditor_manual_review/
│   └── enhance_report.py             # Google Scholar 수동 버전(유지)
├── semantic_scholar_auditor/
│   └── semantic_scholar_report.py     # 새 파일
└── audit_results/
    ├── report.csv                     # 기존 Crossref/DataCite 결과
    ├── report_review.html             # 기존 Google Scholar 판
    ├── report_semantic_scholar.html   # 새로 생성
    └── semantic_scholar_cache.json   # 새로 생성
```

## 사용법 (macOS/Linux)

프로젝트 루트에서:

```bash
# 1. 기존 report.csv가 없을 때만 실행
.venv/bin/python check_bib.py main.bib --out audit_results

# 2. Semantic Scholar 자동 비교
python3 semantic_scholar_auditor/semantic_scholar_report.py \
  audit_results/report.csv --bib main.bib

# 3. 결과 열기 (macOS)
open audit_results/report_semantic_scholar.html
```

**Google Scholar 버전은 그대로 사용합니다:**

```bash
python3 bibtex_auditor_manual_review/enhance_report.py audit_results/report.csv --bib main.bib
open audit_results/report_review.html
```

이 프로그램은 **Python 표준 라이브러리만** 사용하며 별도 pip 패키지가 필요하지 않습니다.

## Semantic Scholar API 키 (선택)

API 키 없이도 일부/대부분 공개 API를 사용할 수 있지만, 공유 unauthenticated limit 및 제한에 의해 429가 발생할 수 있습니다. API 키가 있다면 환경 변수로 지정하세요. 키는 생성된 HTML 또는 캐시에 저장되지 않습니다.

```bash
export SEMANTIC_SCHOLAR_API_KEY='여기에_API_키'
python3 semantic_scholar_auditor/semantic_scholar_report.py audit_results/report.csv --bib main.bib
```

사용 가능한 API 키 요청 및 API 제한 정보: https://www.semanticscholar.org/product/api

## 작동 방식

1. `report.csv`와 `main.bib`의 각 citation key를 연결합니다.
2. BibTeX의 DOI가 있으면 Semantic Scholar `GET /graph/v1/paper/DOI:{doi}`를 먼저 시도합니다.
3. DOI 검색에서 찾지 못하거나 DOI가 없으면 `GET /graph/v1/paper/search/match`로 제목을 검색합니다.
4. `citationStyles.bibtex`가 있으면 API 응답의 **실제 BibTeX 문자열**을 사용합니다. 이 문자열을 임의로 만들어 내지 않습니다.
5. 검색된 후보의 제목 유사도가 90% 미만이거나, DOI·연도의 큰 충돌이 있으면 `AMBIGUOUS`로 표시하고 자동 일치 판정을 보류합니다.
6. 로컬 브라우저 보고서에서 원문을 나란히 표시하고 entry type·모든 필드의 존재 여부 및 내용을 비교합니다. **BibTeX key와 필드 순서는 비교에서 제외**, 값 내 공백 차이만 정규화합니다.

Semantic Scholar가 실제 반환하는 entry type이 `@['JournalArticle', 'Conference']`처럼 비표준일 수도 있습니다. 그대로 표시하며 로컬 표준 entry type과 다르면 `DIFFERENT`로 처리합니다.

### 판정 코드

| 코드 | 의미 |
|---|---|
| `EXACT_TEXT` | 원문 텍스트 일치 (앞뒤 공백 차이 제외) |
| `SAME_FIELDS` | entry type과 모든 필드의 값이 일치; key, 필드 순서, 공백 차이 무시 |
| `DIFFERENT` | 하나 이상의 entry type/필드 값 또는 존재 여부가 다름 |
| `AMBIGUOUS` | 후보 식별 근거 부족 / 연도/DOI 충돌, 비교 판정 보류 |
| `NOT_FOUND` | DOI 및 제목 매칭 실패 |
| `NO_BIBTEX` | 논문 후보는 찾았지만 citationStyles.bibtex가 없음 |
| `API_ERROR` | HTTP 429 등 API 오류 (없는 논문이라는 뜻 아님) |
| `NOT_FETCHED` | 요청 한도/오프라인 모드로 아직 조회하지 않음 |
| `ERROR` | BibTeX 파싱 실패 |

이 자동 판정은 **메타데이터의 동일성**이지 논문의 진위나 인용 적절성을 보증하지 않습니다. `VERIFIED`는 사람의 수동 확인 기록이고, Crossref/DataCite의 기존 `EXACT_TITLE_YEAR` 등과 별개입니다.

### HTML 기능

- 상단 TOTAL/UNVERIFIED/REVIEW/EXACT_TITLE_YEAR/VERIFIED 클릭 필터
- Semantic Scholar 비교 결과별 필터 (불일치, 원문 일치, 후보 모호, API 오류 등)
- 표 열 경계선 드래그 리사이즈
- `main.bib`와 Semantic Scholar API BibTeX 나란히 표시, 불일치 필드 테이블
- `VERIFIED` 수동 체크 시 자동 하단 정렬
- CSV 내보내기, 수동 검증 JSON 백업/복구
- 원본 BibTeX/CSV 변경 없음, Google Scholar 판과 별도 localStorage 키 사용

## 재실행, 캐시, API 오류

첫 실행 시 조회한 결과를 `audit_results/semantic_scholar_cache.json`에 건별로 저장하므로 중단 후 재실행이 가능합니다. 이후 같은 입력에 대해서는 저장된 결과를 사용합니다.

```bash
# 기존 결과를 사용해 HTML만 다시 생성 (인터넷 필요 없음)
python3 semantic_scholar_auditor/semantic_scholar_report.py audit_results/report.csv --bib main.bib --offline

# 모든 논문을 Semantic Scholar API로 다시 조회
python3 semantic_scholar_auditor/semantic_scholar_report.py audit_results/report.csv --bib main.bib --refresh

# 한 번의 실행에서 새 논문 10건 이하만 조회 (분할 실행)
python3 semantic_scholar_auditor/semantic_scholar_report.py audit_results/report.csv --bib main.bib --max-new 10
```

API 속도 제한 준수를 위해 기본적으로 요청 간 최소 약 1초의 간격을 둡니다. 429 및 일부 일시 오류는 소수 재시도하고, 계속 실패하면 해당 항목을 `API_ERROR`로 표시합니다. 네트워크 문제를 실제 문헌 부재로 처리하지 않습니다.

`--offline`으로 실행하면 캐시가 없는 항목은 `NOT_FETCHED`입니다. 캐시 및 HTML의 데이터는 생성 시점의 스냅샷이므로 최신 API 결과를 원할 때 `--refresh`로 재생성하세요.

## 데모 파일

동봉된 `demo/report_semantic_scholar.html`은 **실제 Semantic Scholar 조회 결과가 아닌 테스트용 모의 데이터**입니다. UI 작동 예시로만 사용하고 참고문헌 검증에 사용하지 마세요.

## 보안 및 개인정보

공개 논문의 제목과 DOI가 Semantic Scholar 서버로 전송됩니다. 비공개 원고의 참고문헌에 적용하는 경우 이 점에 유의하세요. API 키는 `SEMANTIC_SCHOLAR_API_KEY` 환경 변수로만 입력합니다. 브라우저의 수동 체크 내역은 로컬 저장소에 남을 수 있으므로 JSON으로 백업하세요.
