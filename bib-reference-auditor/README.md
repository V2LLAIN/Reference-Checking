# BibTeX Reference Auditor

Cross-check every BibTeX entry against Crossref DOI/title records and DataCite DOI records. Generate CSV, JSON, and clickable HTML reports with side-by-side titles and Google Scholar *search links*.

> Google Scholar is NOT automatically queried. This tool cannot certify that all references are valid: absent/mismatched records, preprints, books, conference variants and metadata errors must be checked manually on publisher/proceedings websites.

## Installation (macOS, Linux)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python check_bib.py /path/to/main.bib --out audit_results --email you@university.edu
```

Open `audit_results/report.html` in your browser and inspect `report.csv` for filters. The script never modifies `main.bib`.

## Status definitions

- `EXACT_TITLE_YEAR`: The full title (after decoding BibTeX LaTeX) and year equal the selected external registry record; this does *not* prove every field or the cited claim is accurate.
- `REVIEW`: Difference, ambiguous search result, or missing key comparison. Includes title punctuation/case changes; inspect exact differences in CSV.
- `UNVERIFIED`: No supported metadata match; *not* proof the paper is hallucinated.

Output fields include `title_exact` (case/character-sensitive, NFC Unicode normalized), `title_normalized_equal`, similarity, author, year, venue, DOI, links, issues.

## Limits

- Crossref searches can match unrelated works; first candidates are filtered by title similarity, but manual review remains necessary.
- DataCite is used for exact DOI fallback.
- Conference papers without DOI may need DBLP/proceedings/arXiv validation.
- Publisher metadata can differ from Google Scholar metadata. Exact equality is not always evidence of correctness, and inequality is not always error.
- No auto-fix: safely preserve the original .bib until a human confirms changes.
- Metadata APIs require Internet access. If a request fails, row will be `UNVERIFIED` with an explanatory error.

==================================================================================================================
# BibTeX 참고문헌 검증 도구

모든 BibTeX 항목을 Crossref의 DOI/제목 기록 및 DataCite의 DOI 기록과 교차 검증합니다. 제목을 나란히 비교하고 Google Scholar **검색 링크**를 제공하는 CSV, JSON 및 클릭 가능한 HTML 보고서를 생성합니다.

> Google Scholar를 자동으로 조회하지는 않습니다. 이 도구는 모든 참고문헌의 유효성을 보장할 수 없습니다. 검색되지 않거나 일치하지 않는 기록, 사전 공개 논문(preprint), 도서, 학회별 출판 버전 차이 및 메타데이터 오류는 출판사 또는 학회 프로시딩 웹사이트에서 수동으로 확인해야 합니다.

## 설치 방법 (macOS, Linux)

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python check_bib.py /path/to/main.bib --out audit_results --email you@university.edu
```

브라우저에서 `audit_results/report.html`을 열어 결과를 확인하고, `report.csv`를 이용해 항목을 필터링할 수 있습니다. 이 스크립트는 원본 `main.bib` 파일을 수정하지 않습니다.

## 상태 정의

- `EXACT_TITLE_YEAR`: BibTeX의 LaTeX 표기를 디코딩한 후, 전체 제목과 출판 연도가 선택된 외부 메타데이터 레지스트리의 기록과 정확히 일치합니다. 단, 이것이 모든 필드의 정확성이나 해당 참고문헌이 뒷받침하는 주장의 타당성까지 증명하는 것은 아닙니다.
- `REVIEW`: 정보 불일치, 모호한 검색 결과 또는 비교에 필요한 핵심 정보의 누락을 의미합니다. 제목의 구두점이나 대소문자 차이도 포함됩니다. CSV에서 정확한 차이점을 확인해야 합니다.
- `UNVERIFIED`: 지원되는 외부 메타데이터에서 일치하는 기록을 찾지 못한 상태입니다. 이는 해당 논문이 **존재하지 않는 허위 논문(Hallucinated Paper)**이라는 증거가 아닙니다.

출력 항목에는 `title_exact`(NFC 유니코드 정규화 후 대소문자와 문자 단위로 비교), `title_normalized_equal`, 유사도(similarity), 저자(author), 출판 연도(year), 학회·저널명(venue), DOI, 링크(links), 문제 사항(issues) 등이 포함됩니다.

## 한계점

- Crossref 검색은 관련 없는 논문을 일치하는 결과로 반환할 수 있습니다. 초기 검색 후보는 제목 유사도를 기준으로 필터링하지만, 최종적인 수동 검토는 여전히 필요합니다.
- DataCite는 정확한 DOI 조회가 필요한 경우 대체 검증 수단으로 사용됩니다.
- DOI가 없는 학회 논문은 DBLP, 학회 프로시딩 또는 arXiv를 통한 추가 검증이 필요할 수 있습니다.
- 출판사 메타데이터는 Google Scholar의 메타데이터와 다를 수 있습니다. 정보가 정확히 일치한다고 해서 항상 올바른 것은 아니며, 일치하지 않는다고 해서 반드시 오류가 있는 것도 아닙니다.
- 자동 수정 기능은 제공하지 않습니다. 사용자가 변경 사항을 확인하기 전까지 원본 `.bib` 파일을 안전하게 유지합니다.
- 메타데이터 API를 사용하려면 인터넷 연결이 필요합니다. 요청에 실패한 경우 해당 항목은 `UNVERIFIED`로 표시되며, 오류에 대한 설명이 함께 제공됩니다.
