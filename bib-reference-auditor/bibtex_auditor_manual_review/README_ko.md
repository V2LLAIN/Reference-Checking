# BibTeX Reference Auditor — Manual Review Extension

기존 BibTeX Reference Auditor의 `report.csv`를 이용해 **수동 검증 체크박스가 있는 HTML 대시보드**를 생성합니다. `main.bib` 및 원래 `report.csv`를 수정하지 않습니다.

## 기능

- `UNVERIFIED → REVIEW → EXACT_TITLE_YEAR → VERIFIED` 순서로 실시간 정렬 (미검증 우선)
- 각 논문에 **검증 완료** 체크박스: 체크하면 `VERIFIED`로 바뀌고 표 아래로 즉시 이동
- 체크 해제 시 **원래 자동 검증 상태**로 복원
- 상태별 실시간 건수, 전체 검색/상태 필터, 원본/외부 제목 나란히 보기, Scholar 검색/DOI 링크
- 항목별 검증 근거 메모
- 같은 브라우저에서 로컬 저장소로 체크 상태 보관 (지원되는 경우)
- 검토 기록 JSON 백업 및 복원; 체크 결과가 반영된 CSV 별도 내려받기
- Crossref/DataCite/Scholar **신규 API 호출 없음**; 순수 오프라인 HTML

**주의:** `VERIFIED`는 사용자가 직접 확인했다는 별도 상태입니다. `EXACT_TITLE_YEAR`는 기존 자동 검사 상태이고, 수동 검증의 정확성은 도구가 보증하지 않습니다.

## 설치

Python 표준 라이브러리만 사용합니다. 추가 패키지 설치가 필요하지 않습니다.

프로젝트 루트에서 기존 검사를 실행한 후:

```bash
python3 check_bib.py /path/to/main.bib --out audit_results --email you@university.edu
python3 enhance_report.py audit_results/report.csv
```

그다음 `audit_results/report_review.html`을 브라우저에서 엽니다.

```bash
# macOS
open audit_results/report_review.html

# Linux (데스크톱 환경)
xdg-open audit_results/report_review.html
```

브라우저의 로컬 저장소가 `file://`에서 제한되면, **아래 방법 권장**:

```bash
cd audit_results
python3 -m http.server 8765
```

브라우저에서 `http://localhost:8765/report_review.html` 열기. 이 방식은 저장소를 동일한 로컬 origin에 보관합니다. 다른 브라우저/포트/컴퓨터로 옮길 경우에는 **JSON 백업/복원**을 사용하세요.

## 독립 데모

`report_review_demo.html`을 열면 4개의 **가상 예시 레퍼런스**로 동작을 확인할 수 있습니다. 이 예시 DOI/제목은 실제 문헌 검증 결과가 아닙니다.

## 출력 파일

- `report_review.html`: 인터랙티브 검토 대시보드 (원본 CSV 내용이 HTML에 포함됨)
- HTML의 **검토 결과 CSV 저장**: `report_reviewed.csv`. `original_status`, `display_status`, `manual_verified`, `manual_verified_at`, `manual_note` 컬럼 추가
- HTML의 **체크 상태 백업 JSON**: `manual_review_state.json` (브라우저 재설치, 새 HTML 생성 후 복원 가능)

동일한 BibTeX key를 기준으로 재생성된 리포트에서 수동 검증 상태를 대응시킵니다. 원래 CSV에 key 컬럼이 없다면 제목/DOI/연도로 대체 ID를 생성하므로 원문 변경 시 체크 상태 연결이 달라질 수 있습니다.

## 사용 시 주의사항

1. 브라우저가 로컬 저장을 비활성화했거나 HTML 파일을 다른 환경으로 옮기면 기록이 없어질 수 있습니다. 중요한 검토는 반드시 JSON으로 백업하세요.
2. HTML에 반영된 수동 상태는 **기존 CSV나 `main.bib`에 자동 기록되지 않습니다.** 필요하면 `report_reviewed.csv`를 사용합니다.
3. `EXACT_TITLE_YEAR`는 제목과 연도 일치일 뿐 해당 문헌의 모든 필드나 본문 내 인용의 정확성을 보증하지 않습니다.
4. 직접 만든 report generator 내부 HTML 구조와는 독립적으로 동작합니다. 기존 `report.html` 파일을 직접 수정하는 통합은 `check_bib.py` 원본 코드가 있어야 정확히 적용할 수 있습니다.
