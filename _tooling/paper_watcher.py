"""
paper_watcher.py — weekly candidate scan for the EvidencIA Evidencia section.

This is a curation aid, not an auto-publisher. It queries academic APIs for
new papers on AI + learning, scores them by (a) apparent rigor, (b) empirical
signal, and (c) LAC focus, then posts a short list to the 'paper-candidates'
tab of the data-collection Google Sheet. A human reviews each row and decides
whether to promote it into the site's PAPERS array.

No author allowlist. The filter is entirely on keywords, rigor, and whether
the paper looks empirical.

Sources:
  - Semantic Scholar Graph API (free, no key needed at low volume)
  - OpenAlex API (free, no key needed)

Run:
  python paper_watcher.py                       # dry run, prints to stdout
  python paper_watcher.py --post                # also POSTs to the sheet
  python paper_watcher.py --limit 20            # bigger shortlist for a manual sweep
  python paper_watcher.py --window-days 30      # look 30 days back instead of 7

Notes:
  - Requires only the Python standard library.
  - Deduplicates against papers already in ../index.html so we don't re-surface
    something already curated.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config — the ONLY thing to tune when the shortlist looks off.
# ---------------------------------------------------------------------------

DATA_ENDPOINT = (
    "https://script.google.com/macros/s/"
    "AKfycbw3nqcBepdwlvtScKFFscp23Ddktf0CZJRGj5WzCKWQMLKfDSJ-iewuVyztkcOh2H0t/exec"
)

# What we mean by 'this is about AI in education / learning'.
# All three groups must match at least one term (title OR abstract).
TOPIC_TERMS_AI = [
    "generative ai", "large language model", "llm", "chatgpt", "gpt-4", "gpt-5",
    "claude", "gemini", "llama", "copilot", "ai tutor", "ai tutoring",
    "artificial intelligence",
]
TOPIC_TERMS_EDU = [
    "education", "learning", "classroom", "student", "students", "teacher",
    "teachers", "tutoring", "instruction", "school", "curriculum", "pedagog",
    "higher education", "secondary school", "university",
]

# Rigor signals — presence of any raises the paper's score.
RIGOR_TERMS = [
    "randomized controlled trial", "randomised controlled trial", "rct",
    "randomly assigned", "randomly assigned",
    "quasi-experimental", "difference-in-differences", "difference in differences",
    "diff-in-diff", "regression discontinuity", "instrumental variable",
    "instrumented", "causal effect", "identification strategy",
    "longitudinal", "panel data", "field experiment", "lab experiment",
    "pre-registered", "preregistered",
]

# Terms that mean 'not what we want' — usually theory / opinion / narrative reviews.
NON_EMPIRICAL_TERMS = [
    "commentary", "opinion piece", "position paper", "editorial",
    "conceptual framework only", "theoretical framework",
    "narrative review", "letter to the editor",
]

# LAC bonus — country / language / institution signals.
LAC_TERMS = [
    "latin america", "america latina", "américa latina",
    "argentina", "bolivia", "brazil", "brasil", "chile", "colombia",
    "costa rica", "ecuador", "el salvador", "guatemala", "honduras",
    "mexico", "méxico", "nicaragua", "panama", "paraguay", "peru", "perú",
    "uruguay", "venezuela",
    "espanol", "español", "portugues", "português",
    "banco mundial", "world bank",  # WB LAC often but not exclusive
    "cepal", "eclac", "idb", "bid",
]

MIN_YEAR = 2024   # papers must be at least this recent

# ---------------------------------------------------------------------------
# Fetchers
# ---------------------------------------------------------------------------


def _http_json(url: str, timeout: int = 30, retries: int = 2) -> dict | None:
    """Fetch JSON with a friendly User-Agent so free APIs don't rate-limit us.

    Retries once on 429 with a 5-second backoff — Semantic Scholar's free
    tier is stingy but usually gives in on the second try.
    """
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "EvidencIA-paper-watcher/1.0 (+evidencia landing curation)",
            "Accept": "application/json",
        },
    )
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries:
                time.sleep(5 + 3 * attempt)
                continue
            print(f"  [warn] fetch failed: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"  [warn] fetch failed: {e}", file=sys.stderr)
            return None
    return None


def fetch_semantic_scholar(query: str, limit: int = 40) -> list[dict]:
    """Semantic Scholar bulk search — 100 papers per call, no auth for modest use."""
    fields = ",".join([
        "title", "abstract", "authors", "year", "venue", "url",
        "externalIds", "publicationTypes", "publicationDate",
    ])
    q = urllib.parse.quote_plus(query)
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={q}&limit={limit}&fields={fields}"
    )
    data = _http_json(url)
    if not data or "data" not in data:
        return []
    out = []
    for p in data["data"]:
        authors = ", ".join(a.get("name", "") for a in (p.get("authors") or [])[:6])
        ext = p.get("externalIds") or {}
        out.append({
            "source": "semantic-scholar",
            "title": p.get("title") or "",
            "authors": authors,
            "year": p.get("year"),
            "venue": p.get("venue") or "",
            "url": p.get("url") or "",
            "doi": ext.get("DOI") or "",
            "abstract": p.get("abstract") or "",
        })
    return out


def fetch_openalex(query: str, limit: int = 40) -> list[dict]:
    """OpenAlex — free, better coverage of policy / education working papers."""
    q = urllib.parse.quote_plus(query)
    url = (
        "https://api.openalex.org/works"
        f"?search={q}&per_page={limit}&filter=from_publication_date:{MIN_YEAR}-01-01"
    )
    data = _http_json(url)
    if not data or "results" not in data:
        return []
    out = []
    for w in data["results"]:
        authors = ", ".join(
            (a.get("author") or {}).get("display_name", "")
            for a in (w.get("authorships") or [])[:6]
        )
        venue = (w.get("host_venue") or {}).get("display_name") or ""
        # OpenAlex publication_year is usually int
        year = w.get("publication_year")
        out.append({
            "source": "openalex",
            "title": w.get("title") or "",
            "authors": authors,
            "year": year,
            "venue": venue,
            "url": (w.get("primary_location") or {}).get("landing_page_url")
                   or w.get("id", ""),
            "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
            "abstract": _openalex_reconstruct_abstract(w.get("abstract_inverted_index")),
        })
    return out


def _openalex_reconstruct_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    # inv maps word -> list of positions. Recover the ordered text.
    pos_word = []
    for word, positions in inv.items():
        for p in positions:
            pos_word.append((p, word))
    pos_word.sort()
    return " ".join(w for _, w in pos_word)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


def _matches_any(text: str, terms: list[str]) -> list[str]:
    text = text.lower()
    return [t for t in terms if t in text]


def score_paper(p: dict) -> dict:
    text = f"{p.get('title','')} {p.get('abstract','')}"
    ai_hits = _matches_any(text, TOPIC_TERMS_AI)
    edu_hits = _matches_any(text, TOPIC_TERMS_EDU)
    rigor_hits = _matches_any(text, RIGOR_TERMS)
    non_empirical_hits = _matches_any(text, NON_EMPIRICAL_TERMS)
    lac_hits = _matches_any(text, LAC_TERMS)

    on_topic = bool(ai_hits) and bool(edu_hits)
    rigor_score = min(len(rigor_hits), 5)                # cap so one paper doesn't dominate
    lac_bonus = 3 if lac_hits else 0                     # LAC papers get a clear bump
    non_empirical_penalty = 5 if non_empirical_hits else 0
    total = (2 if on_topic else 0) + rigor_score + lac_bonus - non_empirical_penalty

    return {
        "on_topic": on_topic,
        "rigor_score": rigor_score,
        "lac_bonus": lac_bonus,
        "rigor_hits": rigor_hits,
        "lac_hits": lac_hits,
        "non_empirical_hits": non_empirical_hits,
        "total_score": total,
    }


# ---------------------------------------------------------------------------
# Dedup — parse existing URLs / DOIs / titles out of index.html.
# ---------------------------------------------------------------------------


def load_known(index_path: Path) -> set[str]:
    if not index_path.exists():
        return set()
    text = index_path.read_text(encoding="utf-8", errors="ignore").lower()
    known = set()
    # DOIs
    for m in re.finditer(r"doi\.org/([^'\"\s>]+)", text):
        known.add("doi:" + m.group(1).strip().rstrip("."))
    # arXiv IDs
    for m in re.finditer(r"arxiv\.org/(?:abs|pdf)/([0-9.]+)", text):
        known.add("arxiv:" + m.group(1))
    # SSRN abstract IDs
    for m in re.finditer(r"ssrn\.com/[^'\"]*?abstract_id=([0-9]+)", text):
        known.add("ssrn:" + m.group(1))
    return known


def is_known(p: dict, known: set[str]) -> bool:
    doi = (p.get("doi") or "").lower().strip()
    if doi and ("doi:" + doi) in known:
        return True
    url = (p.get("url") or "").lower()
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9.]+)", url)
    if m and ("arxiv:" + m.group(1)) in known:
        return True
    m = re.search(r"ssrn\.com/[^'\"]*?abstract_id=([0-9]+)", url)
    if m and ("ssrn:" + m.group(1)) in known:
        return True
    return False


# ---------------------------------------------------------------------------
# Post to sheet
# ---------------------------------------------------------------------------


def post_candidate(paper: dict, query: str) -> bool:
    body = json.dumps({
        "type": "paper-candidate",
        "fetchedAt": dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": paper.get("source", ""),
        "query": query,
        "title": paper.get("title", ""),
        "authors": paper.get("authors", ""),
        "year": paper.get("year", ""),
        "venue": paper.get("venue", ""),
        "url": paper.get("url", ""),
        "doi": paper.get("doi", ""),
        "abstract": (paper.get("abstract") or "")[:1500],  # keep the row narrow
        "rigorScore": paper["_score"]["rigor_score"],
        "lacBonus": paper["_score"]["lac_bonus"],
        "totalScore": paper["_score"]["total_score"],
    }).encode("utf-8")
    req = urllib.request.Request(
        DATA_ENDPOINT,
        data=body,
        headers={"Content-Type": "text/plain;charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read().decode("utf-8"))
            return bool(resp.get("ok"))
    except Exception as e:
        print(f"  [warn] post failed: {e}", file=sys.stderr)
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


QUERIES = [
    # One core query + a few sharpened variants. Semantic Scholar / OpenAlex both
    # rank by relevance so wording matters more than length.
    "generative AI education randomized controlled trial",
    "LLM tutoring student learning RCT",
    "ChatGPT classroom impact evaluation empirical",
    "generative AI Latin America education learning",
]


def main() -> int:
    # Windows terminal defaults to cp1252 which chokes on accented chars in
    # paper titles / author names. Force UTF-8 output so the script prints
    # cleanly everywhere.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=8,
                    help="max candidates to write out")
    ap.add_argument("--per-query", type=int, default=25,
                    help="raw results to pull per query per source")
    ap.add_argument("--post", action="store_true",
                    help="also POST winners to the paper-candidates sheet tab")
    ap.add_argument("--min-score", type=int, default=5,
                    help="don't surface anything below this total score")
    args = ap.parse_args()

    root = Path(__file__).resolve().parent.parent
    index_path = root / "index.html"
    known = load_known(index_path)
    print(f"Known items already on site: {len(known)}")

    pool: dict[tuple[str, str], dict] = {}   # key: (title-lower, first-author-lower) -> paper
    used_query_by_key: dict[tuple[str, str], str] = {}
    for i, query in enumerate(QUERIES):
        if i:
            time.sleep(2)  # be nice to the free APIs
        print(f"\nQuery: {query}")
        results = fetch_semantic_scholar(query, args.per_query) \
                + fetch_openalex(query, args.per_query)
        for p in results:
            title = (p.get("title") or "").strip().lower()
            if not title:
                continue
            year = p.get("year")
            if isinstance(year, str) and year.isdigit():
                year = int(year)
            if not year or year < MIN_YEAR:
                continue
            if is_known(p, known):
                continue
            first_author = (p.get("authors") or "").split(",")[0].strip().lower()
            key = (title[:120], first_author[:60])
            if key in pool:
                continue
            score = score_paper(p)
            if not score["on_topic"]:
                continue
            if score["total_score"] < args.min_score:
                continue
            p["_score"] = score
            pool[key] = p
            used_query_by_key[key] = query
        print(f"  cumulative pool: {len(pool)}")

    ranked = sorted(pool.values(), key=lambda x: x["_score"]["total_score"], reverse=True)
    winners = ranked[: args.limit]

    print(f"\nShortlist ({len(winners)}):")
    for i, p in enumerate(winners, 1):
        s = p["_score"]
        marks = []
        if s["lac_bonus"]:
            marks.append("LAC")
        if s["rigor_hits"]:
            marks.append("rigor:" + "/".join(s["rigor_hits"][:3]))
        tag = " · ".join(marks) if marks else "-"
        print(
            f"  {i:>2}. [{s['total_score']:>2}] {p.get('year','?')} · "
            f"{p.get('title','')[:110]}\n"
            f"      {p.get('authors','')[:100]}\n"
            f"      {p.get('url','')}\n"
            f"      {tag}"
        )

    if args.post and winners:
        print("\nPosting to the paper-candidates tab…")
        ok = 0
        for p in winners:
            key = ((p.get("title") or "")[:120].lower(),
                   (p.get("authors") or "").split(",")[0].strip().lower()[:60])
            query = used_query_by_key.get(key, "")
            if post_candidate(p, query):
                ok += 1
        print(f"  posted {ok}/{len(winners)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
