#!/usr/bin/env python3
"""Create an offline, interactive manual review dashboard from BibTeX auditor CSV.

Original report.csv and main.bib are NEVER modified.
Python standard library only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path


def normalize_header(name: str) -> str:
    """Normalize common CSV heading formats, e.g. 'External Registry Title'."""
    return re.sub(r"[^a-z0-9]+", "_", name.casefold()).strip("_")


def pick(record: dict[str, str], *aliases: str) -> str:
    normalized = {normalize_header(k): v for k, v in record.items()}
    for alias in aliases:
        candidate = normalized.get(normalize_header(alias))
        if candidate is not None and str(candidate).strip():
            return str(candidate).strip()
    return ""


def pick_external_title(record: dict[str, str]) -> str:
    """Read a registry title already present in CSV, never guess or copy BibTeX title.

    Reference-auditor versions do not always agree on the CSV column name.
    If the registry metadata was not exported, it must remain visibly missing.
    """
    explicit = pick(
        record, "external_registry_title", "external registry title", "external_title",
        "external_record_title", "external_registry_record_title", "registry_title",
        "registry_record_title", "crossref_title", "crossref_record_title",
        "datacite_title", "datacite_record_title", "matched_title",
        "matched_record_title", "matched_external_title", "matched_registry_title",
        "match_title", "found_title", "best_match_title", "selected_title",
        "candidate_title", "candidate_record_title", "doi_title", "api_title",
        "metadata_title", "official_title", "source_record_title", "ext_title",
        "external_registry_paper_title", "registry_paper_title",
        "title_external", "title_registry", "title_crossref", "title_datacite",
        "external_match_title", "registry_match_title", "registry_matched_title",
        "external_registry_match_title", "crossref_matched_title", "matched_work_title"
    )
    if explicit:
        return explicit
    # Also handle slightly different headings, without accidentally selecting
    # the user's own input/reference/BibTeX title as an external match.
    exclude = {"title", "paper_title", "bib_title", "bibtex_title", "reference_title",
               "original_title", "input_title", "local_title", "provided_title",
               "citation_title", "submitted_title"}
    for field, raw_value in record.items():
        key = normalize_header(field)
        if (key not in exclude and "title" in key and
            any(marker in key for marker in
                ("external", "registry", "crossref", "datacite", "matched", "candidate", "source_record"))
            and raw_value.strip()):
            return raw_value.strip()
    # Optional JSON-in-CSV metadata from other reference auditor variants.
    for field, raw_value in record.items():
        key = normalize_header(field)
        if key not in {"external_record", "registry_record", "crossref_record",
                       "datacite_record", "matched_record", "selected_record", "external_metadata"}:
            continue
        try:
            record_obj = json.loads(raw_value)
            if isinstance(record_obj, dict):
                t = record_obj.get("title", "")
                if isinstance(t, list):
                    t = t[0] if t else ""
                if isinstance(t, str) and t.strip():
                    return t.strip()
        except (ValueError, TypeError, IndexError):
            pass
    return ""

def make_entries(path: Path):
    with path.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            raise SystemExit("CSV 헤더가 없습니다: " + str(path))
        headers = list(reader.fieldnames)
        entries = []
        seen_ids = set()
        key_missing = False
        for index, record in enumerate(reader):
            record = {str(k): ("" if v is None else str(v)) for k, v in record.items() if k is not None}
            key = pick(record, "key", "bibtex_key", "citation_key", "citekey", "entry_key", "bib_key", "id", "entry_id")
            title = pick(record, "bib_title", "bibtex_title", "title_bibtex", "original_title", "input_title", "local_title", "title", "reference_title")
            external = pick_external_title(record)
            doi = pick(record, "doi", "matched_doi", "external_doi")
            year = pick(record, "year", "bib_year", "bibtex_year")
            status = pick(record, "status", "result", "validation_status", "match_status").upper() or "UNVERIFIED"
            if status not in {"EXACT_TITLE_YEAR", "REVIEW", "UNVERIFIED"}:
                # Any unrecognized result gets flagged, not silently approved.
                status = "REVIEW"
            if not key:
                key_missing = True
                stable = f"{title}\x1f{doi}\x1f{year}"
                key = "derived:" + hashlib.sha256(stable.encode('utf-8')).hexdigest()[:20]
            if key in seen_ids:
                raise SystemExit(f"중복 BibTeX 키 발견: {key!r}. 수동 VERIFIED 상태를 안전하게 저장할 수 없습니다.")
            seen_ids.add(key)
            entries.append({
                "key": key,
                "index": index,
                "base_status": status,
                "title": title,
                "external_title": external,
                "year": year,
                "doi": doi,
                "issues": pick(record, "issues", "issue", "warnings", "flags", "error"),
                "scholar_url": pick(record, "scholar_url", "google_scholar_url", "google_scholar_link"),
                "reference_url": pick(record, "crossref_url", "registry_url", "external_url", "doi_url", "url", "source_url"),
                "raw": record,
            })
    return headers, entries, key_missing


STYLES = r'''
:root {color-scheme:light;--ink:#192432;--muted:#687686;--paper:#f4f6f9;--blue:#2457bf;--line:#dfe4ec;--green:#156c53;--amber:#975b13;--red:#a82d43}
* {box-sizing:border-box}body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans KR',sans-serif;margin:0;background:var(--paper);color:var(--ink)}
main{max-width:1460px;margin:auto;padding:28px 22px 64px}h1{font-size:27px;margin:0 0 6px}p{line-height:1.48}.lede{color:var(--muted);margin:0 0 18px}
.toolbar,.stats{display:flex;flex-wrap:wrap;align-items:center;gap:10px;margin:14px 0}
.stat{background:white;border:1px solid var(--line);border-radius:10px;min-width:145px;padding:10px 14px;text-align:left;font-family:inherit;cursor:pointer;transition:border-color .12s, background .12s, box-shadow .12s}
.stat:hover{border-color:#8baadd;background:#f9fbff}.stat:focus-visible{outline:3px solid #8daef1;outline-offset:2px}
.stat.active{border-color:var(--blue);background:#ebf2ff;box-shadow:inset 0 0 0 1px var(--blue)}
.stat .number{font-size:23px;font-weight:750}.stat .label{color:var(--muted);font-size:12px}.stat.active .label{color:#194aab;font-weight:750}
.stat-hint{color:var(--muted);font-size:12px;margin:0 0 4px 2px}
.toolbar{background:white;border:1px solid var(--line);border-radius:11px;padding:12px;gap:8px}input[type='search'],select{border:1px solid #cfd6e0;border-radius:7px;padding:9px 11px;font-size:14px;background:white;color:var(--ink)}input[type='search']{min-width:235px;flex:1}
button,.file-label{border:1px solid #b9c7d9;background:white;color:var(--ink);padding:9px 12px;border-radius:7px;font-size:13px;cursor:pointer;white-space:nowrap}button:hover,.file-label:hover{border-color:var(--blue);color:var(--blue)}.primary{background:var(--blue);color:#fff;border-color:var(--blue)}.primary:hover{background:#183f92;color:white}
.file-label input{display:none}.note{font-size:13px;color:var(--muted);padding:2px 4px}.table-wrap{overflow-x:auto;background:#fff;border:1px solid var(--line);border-radius:11px}table{width:100%;border-collapse:collapse;min-width:1040px;table-layout:fixed}th{position:sticky;top:0;background:#eef2f7;color:#445568;text-align:left;font-size:12px;padding:12px 10px;border-bottom:1px solid var(--line)}td{padding:12px 10px;border-bottom:1px solid #eef0f3;vertical-align:top;font-size:13px;overflow-wrap:anywhere}tbody tr:hover{background:#f9fbfd}tbody tr:last-child td{border-bottom:none}
.missing-registry{color:#8793a1;font-style:italic}.key{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}.title-text{line-height:1.4}.subtle{font-size:12px;color:var(--muted);padding-top:4px}.status{display:inline-block;padding:4px 7px;border-radius:6px;font-size:11px;font-weight:750;letter-spacing:.02em;white-space:nowrap}.status-REVIEW{color:var(--amber);background:#fff0d8}.status-UNVERIFIED{color:var(--red);background:#ffe6ea}.status-EXACT_TITLE_YEAR{color:#42648d;background:#e7effa}.status-VERIFIED{color:var(--green);background:#def5e9}
.verify{display:flex;align-items:center;gap:6px;cursor:pointer;font-weight:650}.verify input{accent-color:var(--green);width:17px;height:17px}.memo{width:100%;border:1px solid #d3d9e1;border-radius:5px;padding:6px 7px;font-size:12px}.links a{display:inline-block;margin:0 9px 6px 0;color:var(--blue);text-decoration:none}.links a:hover{text-decoration:underline}.details{margin-top:5px}.details summary{cursor:pointer;color:#52647f}.details pre{white-space:pre-wrap;word-break:break-word;font-size:11px;line-height:1.5;border:1px solid var(--line);padding:8px;border-radius:6px;background:#f7f9fc}
.msg{font-size:12px;color:var(--green);min-height:18px}.foot{color:var(--muted);font-size:12px;line-height:1.55;margin-top:16px}
@media (max-width:700px){main{padding:16px 10px 40px}h1{font-size:22px}.stat{flex:1;min-width:105px}.toolbar{align-items:stretch}input[type='search']{min-width:100%;flex-basis:100%}}
'''

SCRIPT = r'''
(() => {
 'use strict';
 const payload = JSON.parse(document.getElementById('audit-data').textContent);
 const entries = payload.entries;
 const headers = payload.headers;
 const STORE_KEY = 'bibtex-reference-auditor-manual-v1';
 const priority = {UNVERIFIED:0, REVIEW:1, EXACT_TITLE_YEAR:2, VERIFIED:3};
 let saved = {};
 const $ = id => document.getElementById(id);
 function load() {
   try { const obj = JSON.parse(localStorage.getItem(STORE_KEY) || '{}'); if(obj && typeof obj==='object') saved=obj; }
   catch(err) { $('message').textContent = '이 브라우저에서는 로컬 자동 저장이 제한됩니다. 검토 상태 JSON 내보내기를 사용하세요.'; }
 }
 function persist() {
   try { localStorage.setItem(STORE_KEY, JSON.stringify(saved)); }
   catch(err) { $('message').textContent = '로컬 저장 실패: 검토 상태 JSON을 내려받아 보관하세요.'; }
 }
 function manual(e) { return saved[e.key]?.verified === true; }
 function status(e) { return manual(e) ? 'VERIFIED' : e.base_status; }
 function element(tag, cls, text) {
   const el=document.createElement(tag);
   if(cls) el.className=cls;
   if(text!==undefined) el.textContent=String(text);
   return el;
 }
 function link(text,url) {
   const a=element('a', '', text); a.href=url; a.target='_blank'; a.rel='noopener noreferrer'; return a;
 }
 function urlIsSafe(url) {
   try { return ['https:', 'http:'].includes(new URL(url).protocol); }
   catch { return false; }
 }
 function download(name, content, mime) {
   const blob=new Blob([content],{type:mime});const u=URL.createObjectURL(blob);
   const a=document.createElement('a');a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove();
   setTimeout(()=>URL.revokeObjectURL(u), 3000);
 }
 function say(message) { $('message').textContent=message; }
 function addCell(row,child,className) { const td=element('td',className);td.appendChild(child);row.appendChild(td);return td; }
 function makeRow(e) {
   const row=document.createElement('tr');
   const keyBox=element('div','key',e.key);addCell(row,keyBox);
   const stBox=element('span','status status-'+status(e),status(e));
   const stCell=addCell(row,stBox);stCell.appendChild(element('div','subtle',manual(e)?'Manual review': 'Automated audit'));
   const titleBox=element('div','title-text',e.title || '(제목 없음)');addCell(row,titleBox);
   const extBox=element('div',e.external_title?'title-text':'title-text missing-registry',e.external_title || 'CSV에 외부 제목 정보 없음');addCell(row,extBox);
   addCell(row,element('span','',e.year||'—'));
   const links=element('div','links');
   let scholar=e.scholar_url;
   if(!urlIsSafe(scholar)) scholar='https://scholar.google.com/scholar?q='+encodeURIComponent(e.title || e.key);
   links.appendChild(link('Scholar ↗', scholar));
   let doi=(e.doi||'').replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, '');
   if(doi) links.appendChild(link('DOI ↗','https://doi.org/'+encodeURIComponent(doi).replace(/%2F/g,'/')));
   if(urlIsSafe(e.reference_url)) links.appendChild(link('Source ↗',e.reference_url));
   const det=document.createElement('details');det.className='details';
   const summary=element('summary','','세부 메타데이터'); const pre=element('pre','',JSON.stringify(e.raw,null,2));
   det.append(summary,pre);links.appendChild(det);addCell(row,links);
   addCell(row,element('span','',e.issues||'—'));
   const reviewCell=document.createElement('div');
   const label=element('label','verify'); const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.checked=manual(e);checkbox.setAttribute('aria-label',e.key+' 수동 검증 완료');
   label.append(checkbox,element('span','',checkbox.checked?'확인 완료':'검증 완료'));reviewCell.appendChild(label);
   const memo=document.createElement('input');memo.type='text';memo.className='memo';memo.placeholder='근거 / 검토 메모 (선택)';
   memo.value=saved[e.key]?.note || '';memo.setAttribute('aria-label',e.key+' 검토 메모');memo.style.marginTop='7px';
   memo.addEventListener('change',()=>{const obj=saved[e.key]||{};obj.note=memo.value;saved[e.key]=obj;persist();say('검토 메모가 저장되었습니다.');});
   reviewCell.appendChild(memo);addCell(row,reviewCell);
   checkbox.addEventListener('change',()=>{
     const obj=saved[e.key]||{};obj.verified=checkbox.checked;obj.verified_at=checkbox.checked?new Date().toISOString():null;
     obj.note=memo.value;saved[e.key]=obj;persist();render();
     say(checkbox.checked?`${e.key}: VERIFIED 처리 후 자동 정렬했습니다.`:`${e.key}: 원래 자동 검사 상태로 되돌렸습니다.`);
   });
   return row;
 }
 function render() {
   const counts={UNVERIFIED:0,REVIEW:0,EXACT_TITLE_YEAR:0,VERIFIED:0};
   for(const e of entries) counts[status(e)]++;
   for(const [key,value] of Object.entries(counts)) $("count-"+key).textContent=value;
   $("count-all").textContent=entries.length;
   const search=$('search').value.trim().toLocaleLowerCase();
   const filter=$('filter').value;
   const rows=entries.filter(e=>{
     const s=status(e);
     if(filter==='OPEN' && s!=='REVIEW' && s!=='UNVERIFIED')return false;
     if(filter!=='ALL' && filter!=='OPEN' && filter!==s)return false;
     if(!search)return true;
     return [e.key,e.title,e.external_title,e.year,e.doi,e.issues,s].some(v=>String(v||'').toLocaleLowerCase().includes(search));
   }).sort((a,b)=>priority[status(a)]-priority[status(b)] || a.index-b.index);
   const body=$('audit-rows');body.replaceChildren();
   for(const e of rows)body.appendChild(makeRow(e));
   $('display-count').textContent=`표시: ${rows.length} / ${entries.length}`;
   document.querySelectorAll('.stat[data-filter]').forEach(btn=>{const active=btn.dataset.filter===filter;btn.classList.toggle('active',active);btn.setAttribute('aria-pressed',String(active));});
 }
 function csvEscape(v){const x=String(v??'');return /[",\r\n]/.test(x)?'"'+x.replaceAll('"','""')+'"':x;}
 $('download-csv').addEventListener('click',()=>{
   const extra=['original_status','display_status','manual_verified','manual_verified_at','manual_note'];
   const cols=[...headers,...extra];
   const lines=[cols.map(csvEscape).join(',')];
   for(const e of entries) {
     const obj=saved[e.key]||{};
     const combined={...e.raw,original_status:e.base_status,display_status:status(e),manual_verified:manual(e)?'true':'false',manual_verified_at:obj.verified_at||'',manual_note:obj.note||''};
     lines.push(cols.map(c=>csvEscape(combined[c])).join(','));
   }
   download('report_reviewed.csv','\ufeff'+lines.join('\r\n'),'text/csv;charset=utf-8');
 });
 $('download-json').addEventListener('click',()=>download('manual_review_state.json',JSON.stringify({version:1,exported_at:new Date().toISOString(),entries:saved},null,2),'application/json'));
 $('import-json').addEventListener('change',async ev=>{
   const f=ev.target.files?.[0];if(!f)return;
   try {const obj=JSON.parse(await f.text());
     if(obj.version!==1 || !obj.entries || typeof obj.entries!=='object')throw new Error('지원되지 않는 JSON 형식');
     const valid=new Set(entries.map(e=>e.key));let n=0;
     for(const [k,v] of Object.entries(obj.entries))if(valid.has(k)&&v&&typeof v==='object'){
       saved[k]={verified:v.verified===true,verified_at:typeof v.verified_at==='string'?v.verified_at:null,note:typeof v.note==='string'?v.note:''};n++;
     }
     persist();render();say(`검토 기록 ${n}건을 불러왔습니다.`);
   } catch(err){say('JSON 불러오기 오류: '+err.message);} ev.target.value='';
 });
 $('reset').addEventListener('click',()=>{
   if(!confirm('현재 표시된 리포트의 수동 검증 상태를 모두 초기화할까요? 먼저 JSON 백업을 권장합니다.'))return;
   for(const e of entries)delete saved[e.key];persist();render();say('수동 검증 상태를 초기화했습니다.');
 });
 document.querySelectorAll('.stat[data-filter]').forEach(btn=>btn.addEventListener('click',()=>{$('filter').value=btn.dataset.filter;render();}));
 $('search').addEventListener('input',render);$('filter').addEventListener('change',render);
 load();render();
 if(payload.derived_key_warning)say('주의: CSV에 BibTeX key가 없는 항목이 있습니다. 제목/DOI/연도에서 생성한 ID이므로 원문이 바뀌면 상태 연결이 달라질 수 있습니다.');
})();
'''


def generate(headers, entries, key_missing, title):
    data = {"headers": headers, "entries": entries, "derived_key_warning": key_missing}
    safe_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    safe_json = safe_json.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029','\\u2029')
    stats = ''.join(f'<button type="button" class="stat" data-filter="{name}" aria-pressed="false" title="{name} 상태만 보기"><div id="count-{name}" class="number">0</div><div class="label">{name}</div></button>' for name in ["UNVERIFIED","REVIEW","EXACT_TITLE_YEAR","VERIFIED"])
    return f'''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{STYLES}</style></head>
<body><main><h1>{html.escape(title)}</h1><p class="lede">BibTeX 자동 검증과 수동 확인을 구분하는 오프라인 검토 대시보드 · 미검증 항목이 항상 위쪽</p>
<section class="stats" aria-label="검증 통계 및 상태별 필터"><button type="button" class="stat active" data-filter="ALL" aria-pressed="true" title="모든 참고문헌 보기"><div id="count-all" class="number">0</div><div class="label">TOTAL</div></button>{stats}</section>
<p class="stat-hint">↑ 숫자 카드를 클릭하면 해당 상태만 표시합니다. TOTAL을 누르면 전체 목록으로 돌아갑니다.</p>
<section class="toolbar" aria-label="검토 도구"><input id="search" type="search" placeholder="BibTeX key / 제목 / DOI 검색" aria-label="참고문헌 검색"><select id="filter" aria-label="상태 필터"><option value="ALL">전체 상태</option><option value="OPEN">미검증만 (REVIEW + UNVERIFIED)</option><option value="UNVERIFIED">UNVERIFIED</option><option value="REVIEW">REVIEW</option><option value="EXACT_TITLE_YEAR">EXACT_TITLE_YEAR</option><option value="VERIFIED">VERIFIED</option></select>
<button class="primary" id="download-csv">검토 결과 CSV 저장</button><button id="download-json">체크 상태 백업 JSON</button><label class="file-label">체크 상태 복원 JSON<input id="import-json" type="file" accept=".json,application/json"></label><button id="reset">체크 초기화</button></section>
<p id="display-count" class="note"></p><p id="message" class="msg" role="status" aria-live="polite"></p>
<div class="table-wrap"><table><colgroup><col style="width:12%"><col style="width:11%"><col style="width:19%"><col style="width:20%"><col style="width:5%"><col style="width:13%"><col style="width:10%"><col style="width:10%"></colgroup><thead><tr><th>BibTeX key</th><th>Status</th><th>BibTeX title</th><th>External registry title</th><th>Year</th><th>Links / Raw metadata</th><th>Issues</th><th>Manual verification</th></tr></thead><tbody id="audit-rows"></tbody></table></div>
<p class="foot"><strong>중요:</strong> VERIFIED는 사람이 확인했다는 뜻이며 Crossref/DataCite의 자동 검증 결과(EXACT_TITLE_YEAR)를 변경하지 않습니다. 체크를 해제하면 원래 자동 검증 상태로 되돌아갑니다. 체크 기록은 브라우저 로컬 저장소에 보관될 수 있지만 <code>file://</code> 환경과 브라우저 설정에 따라 보존되지 않을 수 있으므로 반드시 JSON으로 백업하세요. 원본 <code>main.bib</code>과 <code>report.csv</code>는 수정되지 않습니다. Google Scholar 링크는 수동 검색 링크일 뿐 자동 조회하지 않습니다.</p>
</main><script id="audit-data" type="application/json">{safe_json}</script><script>{SCRIPT}</script></body></html>'''


def main():
    ap = argparse.ArgumentParser(description="Turn BibTeX auditor CSV into an offline manual-review dashboard")
    ap.add_argument('csv_path', nargs='?', default='audit_results/report.csv', help='existing report.csv (never changed)')
    ap.add_argument('--out', type=Path, default=None, help='output HTML path (defaults to report_review.html next to CSV)')
    ap.add_argument('--title', default='BibTeX Reference Auditor — Manual Review', help='HTML title')
    args=ap.parse_args()
    src=Path(args.csv_path).expanduser()
    if not src.is_file():ap.error(f'입력 CSV가 존재하지 않습니다: {src}')
    out = args.out or src.with_name('report_review.html')
    headers, entries, missing = make_entries(src)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(generate(headers, entries, missing, args.title), encoding='utf-8')
    print(f'Created: {out.resolve()} ({len(entries)} entries)')
    if missing: print('WARNING: BibTeX key 컬럼을 찾지 못한 항목이 있어 fallback ID가 사용되었습니다.')
    missing_external = sum(not e['external_title'] for e in entries)
    if missing_external:
        print(f'NOTICE: {missing_external}/{len(entries)} entries have no external registry title in report.csv.')
        print('  Available CSV columns: ' + ', '.join(headers))
        print('  If registry titles were not exported by check_bib.py, the auditor must export them first.')


if __name__=='__main__':main()
