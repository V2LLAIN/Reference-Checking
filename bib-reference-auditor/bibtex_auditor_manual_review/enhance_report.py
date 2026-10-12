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

def extract_bibtex_entries(path: Path) -> dict[str, str]:
    """Extract full original BibTeX entry blocks, preserving TeX and field formatting.

    No third-party package required. Supports common brace/parenthesis entry
    delimiters, nested braces, quoted strings, percent comments, and escapes.
    This is a source extractor, not a replacement for BibTeX grammar validation.
    """
    source = path.read_text(encoding="utf-8-sig")
    output: dict[str, str] = {}
    n = len(source)
    i = 0
    while i < n:
        if source[i] != "@":
            i += 1
            continue
        start = i
        j = i + 1
        while j < n and source[j].isalpha():
            j += 1
        entry_type = source[i + 1:j].lower()
        if not entry_type:
            i += 1
            continue
        while j < n and source[j].isspace():
            j += 1
        if j >= n or source[j] not in "{(":
            i += 1
            continue
        opening = source[j]
        closing = "}" if opening == "{" else ")"
        outer_depth = 1
        brace_depth = 0
        in_quote = False
        in_comment = False
        k = j + 1
        while k < n and outer_depth > 0:
            c = source[k]
            if in_comment:
                if c == "\n":
                    in_comment = False
                k += 1
                continue
            if c == "\\":
                k += 2
                continue
            if c == "%" and not in_quote:
                in_comment = True
                k += 1
                continue
            if c == '"' and brace_depth == 0:
                in_quote = not in_quote
                k += 1
                continue
            if not in_quote:
                if opening == "{":
                    if c == "{":
                        outer_depth += 1
                    elif c == "}":
                        outer_depth -= 1
                else:
                    if c == "{":
                        brace_depth += 1
                    elif c == "}" and brace_depth > 0:
                        brace_depth -= 1
                    elif c == "(" and brace_depth == 0:
                        outer_depth += 1
                    elif c == ")" and brace_depth == 0:
                        outer_depth -= 1
            k += 1
        if outer_depth != 0:
            i = j + 1
            continue
        if entry_type not in {"comment", "string", "preamble"}:
            inside = source[j + 1:k - 1]
            key = inside.split(",", 1)[0].strip()
            if key:
                if key in output:
                    raise ValueError(f"Duplicate key in BibTeX source: {key}")
                output[key] = source[start:k].strip()
        i = k
    return output


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
.resizer{position:absolute;right:0;top:0;bottom:0;width:11px;cursor:col-resize;touch-action:none;z-index:2;border-right:2px solid transparent}.resizer:hover,.resizer.dragging{border-right-color:var(--blue);background:#dfeaff88}.table-wrap{scrollbar-gutter:stable}.table-wrap table{min-width:1200px}th{position:sticky;user-select:none}th:last-child .resizer{display:none}body.column-dragging,body.column-dragging *{cursor:col-resize!important;user-select:none!important}.bibtex-pre{white-space:pre-wrap;word-break:break-word;max-height:340px;overflow:auto;font-size:12px;line-height:1.6;border:1px solid var(--line);padding:11px;border-radius:7px;background:#f7f9fc}.bib-ops{display:flex;gap:6px;flex-wrap:wrap;margin:8px 0}.bib-note{color:var(--muted);font-size:12px}.compare-badge{display:inline-block;padding:4px 7px;border-radius:5px;font-size:11px;font-weight:700;margin:3px 0}.compare-not-yet{background:#eff2f6;color:#546779}.compare-same-fields{background:#e4f5ed;color:#156c53}.compare-exact-text{background:#d4f1e0;color:#125d42}.compare-different,.compare-error,.compare-no-main{background:#fff0da;color:#975b13}.compare-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:10px;margin:8px 0}.compare-grid h4{font-size:12px;margin:0 0 5px}.compare-grid pre{margin:0;min-height:90px}.compare-diff{font-size:12px;border:1px solid var(--line);border-radius:6px;padding:8px;margin:8px 0;background:#fff}.compare-diff table{width:100%;min-width:0;table-layout:fixed}.compare-diff th{position:static}.compare-diff td{font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}.bib-paste{display:block;width:100%;min-height:140px;font:12px/1.55 ui-monospace,SFMono-Regular,monospace;border:1px solid var(--line);border-radius:6px;padding:8px;resize:vertical}.msg{font-size:12px;color:var(--green);min-height:18px}.foot{color:var(--muted);font-size:12px;line-height:1.55;margin-top:16px}
@media (max-width:700px){.compare-grid{grid-template-columns:1fr}main{padding:16px 10px 40px}h1{font-size:22px}.stat{flex:1;min-width:105px}.toolbar{align-items:stretch}input[type='search']{min-width:100%;flex-basis:100%}}
'''

SCRIPT = r'''
(() => {
 'use strict';
 const payload = JSON.parse(document.getElementById('audit-data').textContent);
 const entries = payload.entries;
 const headers = payload.headers;
 const STORE_KEY = 'bibtex-reference-auditor-manual-v1';
 const STORE_COLUMNS_KEY = 'bibtex-reference-auditor-columns-v1';
 const WIDTH_RATIOS = [12,11,19,20,5,13,10,10];
 const MIN_WIDTHS = [100,110,180,185,55,145,85,115];
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
 // Scholar has no stable official BibTeX download API. The original main.bib
 // and the BibTeX manually exported from Scholar are parsed and compared locally.
 function parseBibtex(input) {
   if(!input || !input.trim())throw Error('BibTeX가 비어 있습니다.');
   const s=input.trim();let i=0;
   function ws(){while(i<s.length){if(/\s/.test(s[i]))i++;else if(s[i]==='%'){while(i<s.length&&s[i]!=='\n')i++;}else break;}}
   ws();if(s[i]!=='@')throw Error('@로 시작하는 BibTeX entry가 아닙니다.');i++;
   const typ=s.slice(i).match(/^[a-zA-Z]+/);if(!typ)throw Error('Entry 유형이 없습니다.');
   const type=typ[0].toLowerCase();i+=typ[0].length;ws();
   if(s[i]!=='{'&&s[i]!=='(')throw Error('Entry 시작 괄호가 없습니다.');
   const open=s[i++],close=open==='{'?'}':')';ws();
   let key='';while(i<s.length&&s[i]!==','&&s[i]!==close)key+=s[i++];key=key.trim();
   if(!key)throw Error('Citation key가 없습니다.');
   if(s[i]!==',')throw Error('필드가 없거나 BibTeX 헤더가 잘못되었습니다.');i++;
   const fields={};
   function braced(){
     let depth=1,out='';i++;
     while(i<s.length){const c=s[i++];if(c==='\\'){out+=c;if(i<s.length)out+=s[i++];continue;}
       if(c==='{'){depth++;out+=c;continue;}
       if(c==='}'){depth--;if(depth===0)return out;out+=c;continue;}
       out+=c;}
     throw Error('닫히지 않은 중괄호가 있습니다.');
   }
   function quoted(){
     i++;let out='';while(i<s.length){const c=s[i++];if(c==='\\'){out+=c;if(i<s.length)out+=s[i++];continue;}
       if(c==='"')return out;out+=c;}
     throw Error('닫히지 않은 따옴표가 있습니다.');
   }
   function value(){
     let parts=[];while(true){ws();let x='';
       if(s[i]==='{')x=braced();else if(s[i]==='"')x=quoted();
       else {while(i<s.length&&s[i]!==','&&s[i]!==close&&s[i]!=='#')x+=s[i++];x=x.trim();}
       parts.push(x);ws();if(s[i]==='#'){i++;continue;}break;}
     return parts.join(' # ');
   }
   while(true){ws();if(s[i]===','){i++;continue;}
     if(s[i]===close){i++;break;}
     if(i>=s.length)throw Error('Entry 닫는 괄호가 없습니다.');
     const field=s.slice(i).match(/^[\w-]+/);if(!field)throw Error('필드 이름 파싱에 실패했습니다: '+s.slice(i,i+25));
     const name=field[0].toLowerCase();i+=field[0].length;ws();
     if(s[i]!=='=')throw Error(name+' 필드에 = 가 없습니다.');i++;ws();
     if(Object.prototype.hasOwnProperty.call(fields,name))throw Error('중복 필드: '+name);
     fields[name]=value();ws();
     if(s[i]===','){i++;continue;}if(s[i]===close){i++;break;}
     throw Error('필드 '+name+' 뒤에 콤마 또는 닫는 괄호가 없습니다.');
   }
   ws();if(i<s.length)throw Error('여러 BibTeX 엔트리가 붙어 있습니다. 한 개만 입력하세요.');
   return {type,key,fields};
 }
 // Whitespace-only differences do not change a BibTeX field's content.
 // Other changes (braces, TeX commands, case, field presence) remain visible.
 function normalizedField(v){return String(v).replace(/\r\n?/g,'\n').replace(/\s+/g,' ').trim();}
 function scholarComparison(e) {
   const other=saved[e.key]?.scholar_bibtex;
   if(!other)return {code:'NOT_YET',label:'Scholar 비교 전',differences:[]};
   if(!e.bibtex)return {code:'NO_MAIN',label:'main.bib 원문 없음',differences:[]};
   try {
     const local=parseBibtex(e.bibtex),remote=parseBibtex(other);
     const differences=[];
     if(local.type!==remote.type)differences.push({field:'entry type',local:local.type,scholar:remote.type});
     const fields=new Set([...Object.keys(local.fields),...Object.keys(remote.fields)]);
     for(const field of [...fields].sort()) {
       const lv=Object.prototype.hasOwnProperty.call(local.fields,field)?normalizedField(local.fields[field]):'(필드 없음)';
       const rv=Object.prototype.hasOwnProperty.call(remote.fields,field)?normalizedField(remote.fields[field]):'(필드 없음)';
       if(lv!==rv)differences.push({field,local:lv,scholar:rv});
     }
     // Exact textual equality includes citation key, layout and all characters.
     // Field equality deliberately ignores BibTeX citekey, field order and whitespace-only differences.
     const exact=e.bibtex.replace(/\r\n?/g,'\n').trim()===other.replace(/\r\n?/g,'\n').trim();
     return {code:exact?'EXACT_TEXT':differences.length?'DIFFERENT':'SAME_FIELDS',
       label:exact?'원문 완전 일치':differences.length?'필드 불일치 '+differences.length+'건':'모든 필드 일치',
       differences,localKey:local.key,scholarKey:remote.key};
   } catch(err){return {code:'ERROR',label:'비교 불가: 파싱 오류',reason:String(err.message||err),differences:[]};}
 }
 function addBibtexViewer(e, links) {
   const det=element('details','details');det.appendChild(element('summary','','BibTeX 원문 및 Scholar 비교'));
   const badge=element('span','compare-badge');links.appendChild(badge);
   const hint=element('div','bib-note','Google Scholar 검색 → 인용(Cite) → BibTeX → 복사 → 아래에 붙여넣기. Scholar 자동 수집은 하지 않습니다.');
   det.appendChild(hint);
   const grid=element('div','compare-grid');
   const mainBox=element('div','');mainBox.appendChild(element('h4','','main.bib (원본)'));
   const mainPre=element('pre','bibtex-pre',e.bibtex||'(원문 없음: --bib main.bib 사용)');mainBox.appendChild(mainPre);
   const scholarBox=element('div','');scholarBox.appendChild(element('h4','','Google Scholar BibTeX (붙여넣은 내용)'));
   const scholarPre=element('pre','bibtex-pre');scholarBox.appendChild(scholarPre);
   grid.append(mainBox,scholarBox);det.appendChild(grid);
   const comparisonNote=element('div','bib-note');det.appendChild(comparisonNote);
   const diffPanel=element('div','compare-diff');det.appendChild(diffPanel);
   function updateCompareView(){
     const scholar=saved[e.key]?.scholar_bibtex||'';
     scholarPre.textContent=scholar||'(Scholar에서 복사한 BibTeX를 등록하지 않았습니다.)';
     const cmp=scholarComparison(e);
     const cls={NOT_YET:'compare-not-yet',NO_MAIN:'compare-no-main',ERROR:'compare-error',DIFFERENT:'compare-different',SAME_FIELDS:'compare-same-fields',EXACT_TEXT:'compare-exact-text'};
     badge.className='compare-badge '+cls[cmp.code];badge.textContent=cmp.label;
     diffPanel.replaceChildren();
     if(cmp.code==='EXACT_TEXT')comparisonNote.textContent='key, 필드 순서, 공백, 모든 문자가 동일합니다.';
     else if(cmp.code==='SAME_FIELDS')comparisonNote.textContent='Entry 유형 및 모든 필드 값이 일치합니다. Citation key, 필드 순서, 공백은 다를 수 있습니다.';
     else if(cmp.code==='DIFFERENT')comparisonNote.textContent='정확 비교 실패. 아래에 일치하지 않는 모든 필드를 표시합니다.';
     else if(cmp.code==='ERROR')comparisonNote.textContent=cmp.reason;
     else comparisonNote.textContent='Scholar BibTeX와 main.bib 원문이 모두 있어야 비교할 수 있습니다.';
     if(cmp.scholarKey&&cmp.localKey&&cmp.scholarKey!==cmp.localKey){
       diffPanel.appendChild(element('div','bib-note','참고: citation key 차이는 필드 일치 판정에서 제외합니다. main.bib: '+cmp.localKey+' / Scholar: '+cmp.scholarKey));
     }
     if(cmp.differences.length){
       const table=element('table','');const h=element('tr','');
       ['필드','main.bib','Google Scholar'].forEach(x=>h.appendChild(element('th','',x)));table.appendChild(h);
       for(const d of cmp.differences){const tr=element('tr','');
         [d.field,d.local,d.scholar].forEach(v=>tr.appendChild(element('td','',v)));table.appendChild(tr);}
       diffPanel.appendChild(table);
     } else if(cmp.code==='SAME_FIELDS'||cmp.code==='EXACT_TEXT')diffPanel.appendChild(element('div','', '비교한 필드에 불일치가 없습니다.'));
     diffPanel.hidden=!diffPanel.textContent.trim();
   }
   const actions=element('div','bib-ops');
   const copy=element('button','','main.bib 복사');copy.type='button';copy.disabled=!e.bibtex;
   copy.addEventListener('click',async()=>{
     try {await navigator.clipboard.writeText(e.bibtex);say(e.key+' main.bib 원문을 복사했습니다.');}
     catch{say('클립보드 복사가 제한되었습니다. 위 원문을 선택해 복사하세요.');}
   });actions.appendChild(copy);
   const edit=element('button','','Scholar BibTeX 입력 / 변경');edit.type='button';actions.appendChild(edit);
   const pasteArea=element('div','');pasteArea.hidden=true;
   const ta=element('textarea','bib-paste');ta.placeholder='Google Scholar에서 내보낸 @article{...} 또는 @inproceedings{...} 전체를 붙여넣으세요.';pasteArea.appendChild(ta);
   const pasteActions=element('div','bib-ops');
   const save=element('button','primary','비교 실행 및 저장');save.type='button';
   save.addEventListener('click',()=>{
     const v=ta.value.trim();
     if(v){try{parseBibtex(v);}catch(err){say('Scholar BibTeX 파싱 실패: '+err.message);return;}}
     const obj=saved[e.key]||{};
     if(v)obj.scholar_bibtex=v;else delete obj.scholar_bibtex;
     saved[e.key]=obj;persist();pasteArea.hidden=true;updateCompareView();
     const cmp=scholarComparison(e);
     say(e.key+': '+cmp.label+'. 원본 main.bib은 변경되지 않았습니다.');
   });pasteActions.appendChild(save);
   const cancel=element('button','','취소');cancel.type='button';cancel.addEventListener('click',()=>{pasteArea.hidden=true;});pasteActions.appendChild(cancel);
   pasteArea.appendChild(pasteActions);
   edit.addEventListener('click',()=>{pasteArea.hidden=!pasteArea.hidden;if(!pasteArea.hidden){ta.value=saved[e.key]?.scholar_bibtex||'';ta.focus();}});
   det.appendChild(actions);det.appendChild(pasteArea);
   updateCompareView();links.appendChild(det);
 }
 function initColumnResize() {
   const table=$('audit-table');
   const cols=Array.from(table.querySelectorAll('colgroup col'));
   const heads=Array.from(table.querySelectorAll('thead th'));
   const totalWidth=Math.max(1200, table.getBoundingClientRect().width);
   let widths=WIDTH_RATIOS.map(v=>Math.round(totalWidth*v/100));
   // Roundoff correction to keep the same table width.
   widths[widths.length-1] += totalWidth-widths.reduce((a,b)=>a+b,0);
   try {
     const data=JSON.parse(localStorage.getItem(STORE_COLUMNS_KEY)||'null');
     if(Array.isArray(data) && data.length===cols.length && data.every((v,i)=>Number.isFinite(v)&&v>=MIN_WIDTHS[i]))widths=data;
   }catch{}
   function apply(){
     const sum=widths.reduce((a,b)=>a+b,0);
     table.style.width=sum+'px';
     cols.forEach((col,i)=>{col.style.width=widths[i]+'px';});
   }
   apply();
   heads.forEach((th,i)=>{
     if(i>=cols.length-1)return;
     const handle=element('span','resizer');
     handle.title='드래그하여 두 열의 너비 조절';
     handle.setAttribute('role','separator');handle.setAttribute('aria-label',th.textContent+' 열 너비 조절');
     handle.tabIndex=0;
     th.appendChild(handle);
     function resizeDelta(delta){
       const d=Math.min(Math.max(delta,MIN_WIDTHS[i]-widths[i]),widths[i+1]-MIN_WIDTHS[i+1]);
       widths[i]+=d;widths[i+1]-=d;apply();
     }
     handle.addEventListener('pointerdown',ev=>{
       if(ev.button!==0)return;
       ev.preventDefault();ev.stopPropagation();
       const origX=ev.clientX, startLeft=widths[i],startRight=widths[i+1];
       handle.setPointerCapture(ev.pointerId);
       handle.classList.add('dragging');document.body.classList.add('column-dragging');
       const onMove=e=>{widths[i]=startLeft;widths[i+1]=startRight;resizeDelta(e.clientX-origX);};
       const onDone=()=>{handle.classList.remove('dragging');document.body.classList.remove('column-dragging');handle.removeEventListener('pointermove',onMove);handle.removeEventListener('pointerup',onDone);handle.removeEventListener('pointercancel',onDone);try{localStorage.setItem(STORE_COLUMNS_KEY,JSON.stringify(widths));}catch{say('열 너비 자동 저장 불가');}};
       handle.addEventListener('pointermove',onMove);handle.addEventListener('pointerup',onDone);handle.addEventListener('pointercancel',onDone);
     });
     handle.addEventListener('keydown',ev=>{
       if(ev.key!=='ArrowLeft'&&ev.key!=='ArrowRight')return;
       ev.preventDefault();resizeDelta(ev.key==='ArrowLeft'?-16:16);
       try{localStorage.setItem(STORE_COLUMNS_KEY,JSON.stringify(widths));}catch{}
     });
   });
   $('reset-columns').addEventListener('click',()=>{
     const w=Math.max(1200,table.parentElement.clientWidth);
     widths=WIDTH_RATIOS.map(v=>Math.round(w*v/100));
     widths[widths.length-1]+=w-widths.reduce((a,b)=>a+b,0);
     apply();try{localStorage.removeItem(STORE_COLUMNS_KEY);}catch{}
     say('열 너비를 기본값으로 복원했습니다.');
   });
 }

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
   addBibtexViewer(e,links);addCell(row,links);
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
   const extra=['original_status','display_status','manual_verified','manual_verified_at','manual_note','scholar_bibtex_comparison','scholar_bibtex_differences','scholar_bibtex'];
   const cols=[...headers,...extra];
   const lines=[cols.map(csvEscape).join(',')];
   for(const e of entries) {
     const obj=saved[e.key]||{};
     const cmp=scholarComparison(e);
     const combined={...e.raw,original_status:e.base_status,display_status:status(e),manual_verified:manual(e)?'true':'false',manual_verified_at:obj.verified_at||'',manual_note:obj.note||'',scholar_bibtex_comparison:cmp.code,scholar_bibtex_differences:JSON.stringify(cmp.differences),scholar_bibtex:obj.scholar_bibtex||''};
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
       saved[k]={verified:v.verified===true,verified_at:typeof v.verified_at==='string'?v.verified_at:null,note:typeof v.note==='string'?v.note:'', scholar_bibtex:typeof v.scholar_bibtex==='string'?v.scholar_bibtex:''};n++;
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
 load();initColumnResize();render();
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
<p class="stat-hint">↑ 숫자 카드로 상태 필터링 · 표 헤더의 오른쪽 경계선을 드래그하면 열 너비 조절 · Scholar BibTeX를 붙여넣으면 main.bib 원문과 모든 필드를 비교합니다.</p>
<section class="toolbar" aria-label="검토 도구"><input id="search" type="search" placeholder="BibTeX key / 제목 / DOI 검색" aria-label="참고문헌 검색"><select id="filter" aria-label="상태 필터"><option value="ALL">전체 상태</option><option value="OPEN">미검증만 (REVIEW + UNVERIFIED)</option><option value="UNVERIFIED">UNVERIFIED</option><option value="REVIEW">REVIEW</option><option value="EXACT_TITLE_YEAR">EXACT_TITLE_YEAR</option><option value="VERIFIED">VERIFIED</option></select>
<button class="primary" id="download-csv">검토 결과 CSV 저장</button><button id="download-json">체크 상태 백업 JSON</button><label class="file-label">체크 상태 복원 JSON<input id="import-json" type="file" accept=".json,application/json"></label><button id="reset">체크 초기화</button><button id="reset-columns">열 너비 초기화</button></section>
<p id="display-count" class="note"></p><p id="message" class="msg" role="status" aria-live="polite"></p>
<div class="table-wrap"><table id="audit-table"><colgroup><col style="width:12%"><col style="width:11%"><col style="width:19%"><col style="width:20%"><col style="width:5%"><col style="width:13%"><col style="width:10%"><col style="width:10%"></colgroup><thead><tr><th>BibTeX key</th><th>Status</th><th>BibTeX title</th><th>External registry title</th><th>Year</th><th>Links / BibTeX</th><th>Issues</th><th>Manual verification</th></tr></thead><tbody id="audit-rows"></tbody></table></div>
<p class="foot"><strong>중요:</strong> VERIFIED는 사람이 확인했다는 뜻이며 Crossref/DataCite의 자동 검증 결과(EXACT_TITLE_YEAR)를 변경하지 않습니다. 체크를 해제하면 원래 자동 검증 상태로 되돌아갑니다. 체크 기록은 브라우저 로컬 저장소에 보관될 수 있지만 <code>file://</code> 환경과 브라우저 설정에 따라 보존되지 않을 수 있으므로 반드시 JSON으로 백업하세요. 원본 <code>main.bib</code>과 <code>report.csv</code>는 수정되지 않습니다. Google Scholar는 자동으로 조회하지 않습니다. Scholar → Cite → BibTeX에서 복사해 붙여넣으면 모든 필드를 비교하며, citation key/순서/공백 차이도 구분합니다. 비교 일치만으로 수동 VERIFIED가 부여되지는 않습니다. <code>--bib main.bib</code>로 원본 BibTeX를 표시하거나 Scholar에서 복사한 BibTeX를 논문별로 붙여넣을 수 있습니다. 열 너비는 브라우저에 저장됩니다.</p>
</main><script id="audit-data" type="application/json">{safe_json}</script><script>{SCRIPT}</script></body></html>'''


def main():
    ap = argparse.ArgumentParser(description="Turn BibTeX auditor CSV into an offline manual-review dashboard")
    ap.add_argument('csv_path', nargs='?', default='audit_results/report.csv', help='existing report.csv (never changed)')
    ap.add_argument('--out', type=Path, default=None, help='output HTML path (defaults to report_review.html next to CSV)')
    ap.add_argument('--bib', type=Path, default=None, help='original main.bib to display full BibTeX entries; Scholar is not queried')
    ap.add_argument('--title', default='BibTeX Reference Auditor — Manual Review', help='HTML title')
    args=ap.parse_args()
    src=Path(args.csv_path).expanduser()
    if not src.is_file():ap.error(f'입력 CSV가 존재하지 않습니다: {src}')
    out = args.out or src.with_name('report_review.html')
    headers, entries, missing = make_entries(src)
    bib_path = args.bib.expanduser() if args.bib else None
    if bib_path is None:
        for candidate in (src.parent.parent / 'main.bib', src.parent / 'main.bib', Path('main.bib')):
            if candidate.is_file():
                bib_path = candidate
                break
    if bib_path is not None:
        if not bib_path.is_file(): ap.error(f'BibTeX 파일이 존재하지 않습니다: {bib_path}')
        try: raw_bib = extract_bibtex_entries(bib_path)
        except (OSError, ValueError) as exc: ap.error(str(exc))
    else:
        raw_bib = {}
    for e in entries:
        e['bibtex'] = raw_bib.get(e['key'], '')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(generate(headers, entries, missing, args.title), encoding='utf-8')
    print(f'Created: {out.resolve()} ({len(entries)} entries)')
    print(f'BibTeX source: {bib_path if bib_path else "not found"} ({sum(bool(e["bibtex"]) for e in entries)}/{len(entries)} entries matched)')
    if missing: print('WARNING: BibTeX key 컬럼을 찾지 못한 항목이 있어 fallback ID가 사용되었습니다.')
    missing_external = sum(not e['external_title'] for e in entries)
    if missing_external:
        print(f'NOTICE: {missing_external}/{len(entries)} entries have no external registry title in report.csv.')
        print('  Available CSV columns: ' + ', '.join(headers))
        print('  If registry titles were not exported by check_bib.py, the auditor must export them first.')


if __name__=='__main__':main()
