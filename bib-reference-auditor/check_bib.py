#!/usr/bin/env python3
"""Audit BibTeX references against DOI registry metadata without scraping Google Scholar."""
import argparse
import csv
import difflib
import html
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote, urlencode

import requests
from pybtex.database import parse_file
from pylatexenc.latex2text import LatexNodes2Text

LATEX = LatexNodes2Text()
HEADERS = {"User-Agent": "BibReferenceAuditor/0.1 (research citation verification)"}
FIELDS = ["key", "status", "source", "match_method", "bib_title", "reference_title", "title_exact", "title_normalized_equal", "title_similarity", "bib_year", "reference_year", "year_equal", "bib_first_author", "reference_first_author", "first_author_equal", "bib_venue", "reference_venue", "venue_similarity", "bib_doi", "reference_doi", "reference_url", "scholar_url", "issues"]


def plain(s):
    s = str(s or "")
    try:
        s = LATEX.latex_to_text(s)
    except Exception:
        pass
    return unicodedata.normalize("NFC", s).strip()


def norm(s):
    s = plain(s).casefold()
    s = re.sub(r"[^\w\s]", " ", s, flags=re.UNICODE)
    return " ".join(s.split())


def similarity(a, b):
    return round(difflib.SequenceMatcher(None, norm(a), norm(b)).ratio(), 4) if a and b else 0.0


def clean_doi(doi):
    doi = plain(doi).strip()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi, flags=re.I)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.I)
    return doi.strip().lower()


def request_json(session, url, params=None, retries=2):
    for attempt in range(retries + 1):
        try:
            response = session.get(url, params=params, timeout=16)
            if response.status_code == 404:
                return None
            if response.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(min(8, 1.5 * (attempt + 1)))
                continue
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            if attempt == retries:
                raise RuntimeError(f"{type(exc).__name__}: {exc}") from exc
            time.sleep(attempt + 1)
    return None


def crossref_record(item):
    if not item:
        return None
    dates = item.get("published") or item.get("published-print") or item.get("published-online") or item.get("issued") or {}
    parts = dates.get("date-parts") or [[]]
    year = str(parts[0][0]) if parts and parts[0] else ""
    authors = item.get("author") or []
    first = authors[0].get("family") or authors[0].get("name") or "" if authors else ""
    return {
        "source": "Crossref", "title": plain((item.get("title") or [""])[0]),
        "year": year, "first_author": plain(first),
        "venue": plain((item.get("container-title") or [""])[0]),
        "doi": clean_doi(item.get("DOI", "")),
        "url": item.get("URL") or ("https://doi.org/" + item["DOI"] if item.get("DOI") else ""),
    }


def datacite_record(item):
    if not item:
        return None
    attr = item.get("data", {}).get("attributes", {})
    authors = attr.get("creators") or []
    first = authors[0].get("familyName") or authors[0].get("name") or "" if authors else ""
    titles = attr.get("titles") or []
    venue = attr.get("container", {}) or {}
    return {
        "source": "DataCite", "title": plain(titles[0].get("title", "") if titles else ""),
        "year": str(attr.get("publicationYear") or ""), "first_author": plain(first),
        "venue": plain(venue.get("title", "")),
        "doi": clean_doi(attr.get("doi", "")),
        "url": attr.get("url") or ("https://doi.org/" + attr["doi"] if attr.get("doi") else ""),
    }


def lookup(session, entry, delay):
    doi = clean_doi(entry.fields.get("doi", ""))
    title = plain(entry.fields.get("title", ""))
    errors = []
    candidates = []
    if doi:
        try:
            data = request_json(session, "https://api.crossref.org/works/" + quote(doi, safe=""))
            if data:
                candidates.append((crossref_record(data["message"]), "doi"))
        except (RuntimeError, KeyError, ValueError) as e:
            errors.append("Crossref DOI lookup: " + str(e))
        time.sleep(delay)
        if not candidates:
            try:
                data = request_json(session, "https://api.datacite.org/dois/" + quote(doi, safe=""))
                if data:
                    candidates.append((datacite_record(data), "doi"))
            except (RuntimeError, KeyError, ValueError) as e:
                errors.append("DataCite DOI lookup: " + str(e))
            time.sleep(delay)
    if not candidates and title:
        try:
            data = request_json(session, "https://api.crossref.org/works", {"query.bibliographic": title, "rows": 5})
            for item in (data or {}).get("message", {}).get("items", []):
                rec = crossref_record(item)
                if rec:
                    candidates.append((rec, "title_search"))
        except (RuntimeError, KeyError, ValueError) as e:
            errors.append("Crossref title search: " + str(e))
        time.sleep(delay)
    if not candidates:
        return None, "", errors
    candidates.sort(key=lambda c: similarity(title, c[0]["title"]), reverse=True)
    return candidates[0][0], candidates[0][1], errors


def audit(key, entry, ref, method, errors):
    title = plain(entry.fields.get("title", ""))
    year = plain(entry.fields.get("year", "")) or plain(entry.fields.get("date", ""))[:4]
    doi = clean_doi(entry.fields.get("doi", ""))
    venue = plain(entry.fields.get("booktitle", "") or entry.fields.get("journal", ""))
    people = entry.persons.get("author", [])
    first = plain(str(people[0].last_names[0])) if people and people[0].last_names else ""
    scholar_url = "https://scholar.google.com/scholar?" + urlencode({"q": '"' + title + '"'})
    row = {c: "" for c in FIELDS}
    row.update(key=key, bib_title=title, bib_year=year, bib_first_author=first,
               bib_venue=venue, bib_doi=doi, scholar_url=scholar_url, match_method=method)
    issues = list(errors)
    if not title:
        issues.append("Missing BibTeX title")
    if not ref:
        row["status"] = "UNVERIFIED"
        issues.append("No reliable registry match; NOT proof that the paper is nonexistent")
        row["issues"] = "; ".join(issues)
        return row
    row.update(source=ref["source"], reference_title=ref["title"], reference_year=ref["year"],
               reference_first_author=ref["first_author"], reference_venue=ref["venue"],
               reference_doi=ref["doi"], reference_url=ref["url"],
               title_exact=str(title == ref["title"]),
               title_normalized_equal=str(norm(title) == norm(ref["title"])),
               title_similarity=similarity(title, ref["title"]),
               year_equal=str(year == ref["year"]) if year and ref["year"] else "",
               first_author_equal=str(norm(first) == norm(ref["first_author"])) if first and ref["first_author"] else "",
               venue_similarity=similarity(venue, ref["venue"]) if venue and ref["venue"] else "")
    if not title == ref["title"]:
        issues.append("Title differs character-for-character")
    if doi and ref["doi"] and doi != ref["doi"]:
        issues.append("DOI mismatch")
    if year and ref["year"] and year != ref["year"]:
        issues.append("Year mismatch (preprint/online/proceedings variants possible)")
    if first and ref["first_author"] and norm(first) != norm(ref["first_author"]):
        issues.append("First author mismatch")
    if method == "title_search" and similarity(title, ref["title"]) < 0.9:
        issues.append("Weak candidate match: do not treat as verified")
    if method == "doi" and similarity(title, ref["title"]) < 0.8:
        issues.append("DOI resolves to substantially different title")
    serious = any(k in x for x in issues for k in ("mismatch", "Weak candidate", "substantially different"))
    if serious or (method == "title_search" and similarity(title, ref["title"]) < 0.9):
        row["status"] = "REVIEW"
    elif title == ref["title"] and year and ref["year"] and year == ref["year"]:
        row["status"] = "EXACT_TITLE_YEAR"
    else:
        row["status"] = "REVIEW"
    if not doi:
        issues.append("BibTeX DOI missing")
    if not first or not ref["first_author"]:
        issues.append("First-author comparison unavailable")
    if not venue or not ref["venue"]:
        issues.append("Venue comparison unavailable")
    row["issues"] = "; ".join(issues)
    return row


def write_html(rows, output):
    colors = {"EXACT_TITLE_YEAR": "#166534", "REVIEW": "#9a3412", "UNVERIFIED": "#991b1b"}
    def esc(x):
        return html.escape(str(x or ""))
    lines = ['<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BibTeX Audit</title>',
             '<style>body{font:14px system-ui;margin:30px auto;max-width:1200px;padding:0 18px;color:#172033}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #ddd;padding:9px;text-align:left;vertical-align:top}th{position:sticky;top:0;background:#f5f7fb}a{color:#164f9d}small{color:#666}</style>',
             '<h1>BibTeX reference audit</h1><p>Registry metadata comparison, not Google Scholar verification. Review flagged references manually at the publisher or proceedings site.</p>',
             '<table><thead><tr><th>Key</th><th>Status</th><th>BibTeX title</th><th>Registry title</th><th>Checks / issues</th><th>Links</th></tr></thead><tbody>']
    for r in rows:
        color = colors.get(r["status"], "#555")
        links = f'<a href="{esc(r["scholar_url"])}">Scholar search</a>'
        if r["reference_url"]:
            links += f' · <a href="{esc(r["reference_url"])}">{esc(r["source"] or "record")}</a>'
        lines.append(f'<tr><td><code>{esc(r["key"])}</code></td><td style="color:{color}"><b>{esc(r["status"])}</b></td><td>{esc(r["bib_title"])}</td><td>{esc(r["reference_title"])}</td><td>{esc(r["issues"])}</td><td>{links}</td></tr>')
    lines.append('</tbody></table></html>')
    output.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Audit BibTeX metadata against Crossref and DataCite; provide Scholar search links")
    parser.add_argument("bib", type=Path, help="Input .bib file")
    parser.add_argument("--out", type=Path, default=Path("audit_results"))
    parser.add_argument("--email", default="", help="Contact email for Crossref polite API pool")
    parser.add_argument("--delay", type=float, default=0.25, help="Seconds between API calls")
    args = parser.parse_args()
    if not args.bib.exists():
        parser.error(f"File not found: {args.bib}")
    args.out.mkdir(parents=True, exist_ok=True)
    database = parse_file(str(args.bib), bib_format="bibtex")
    session = requests.Session()
    session.headers.update(HEADERS)
    if args.email:
        session.headers["User-Agent"] += " (mailto:" + args.email + ")"
    rows = []
    for i, (key, entry) in enumerate(database.entries.items(), 1):
        print(f"[{i}/{len(database.entries)}] {key}", flush=True)
        ref, method, errors = lookup(session, entry, max(args.delay, 0))
        rows.append(audit(key, entry, ref, method, errors))
    with (args.out / "report.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (args.out / "report.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    write_html(rows, args.out / "report.html")
    for status in ("EXACT_TITLE_YEAR", "REVIEW", "UNVERIFIED"):
        print(f"{status}: {sum(r['status'] == status for r in rows)}")
    print(f"Reports: {args.out.resolve()}")


if __name__ == "__main__":
    main()
