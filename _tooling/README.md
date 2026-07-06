# `_tooling/` — curation aids for EvidencIA

Scripts that help curate the `PAPERS` array in `../index.html`. Nothing here
is served on the site; this folder is a workshop, not a build step.

## paper_watcher.py

Weekly-ish scan for candidate papers to add to the Evidencia section.
Queries [Semantic Scholar](https://api.semanticscholar.org/) and
[OpenAlex](https://api.openalex.org/), filters by keyword + rigor terms,
excludes anything that looks like an opinion piece / narrative review /
theoretical framework, gives a bump to Latin America — Caribbean papers,
deduplicates against what's already linked in `index.html`, and prints
(or POSTs to the sheet) a short shortlist.

**No author allowlist**. The filter is entirely keywords, rigor terms,
and empirical signal.

### Requirements

- Python 3.10+
- Only the standard library — no `pip install` needed.

### Run

```bash
# dry run — just prints the shortlist
python _tooling/paper_watcher.py

# post the shortlist to the 'paper-candidates' tab of the sheet
python _tooling/paper_watcher.py --post

# wider net for a manual sweep (default limit is 8)
python _tooling/paper_watcher.py --limit 20 --min-score 3
```

Each posted row goes to the `paper-candidates` tab of the
**EvidencIA — data collection** Google Sheet with three empty columns at
the end (Reviewed / Decision / Notes) so you can hand-annotate what
gets promoted.

### Tune

The only thing to touch when the shortlist drifts off-topic is the block
of constants at the top of `paper_watcher.py`:

- `TOPIC_TERMS_AI` and `TOPIC_TERMS_EDU` — both must match for a paper
  to be considered on topic.
- `RIGOR_TERMS` — presence of any of these bumps the score.
- `NON_EMPIRICAL_TERMS` — presence of any of these penalises the paper
  hard, so opinion / theory / commentary papers drop out.
- `LAC_TERMS` — presence adds a `+3` LAC bonus. Priorities regional
  papers without excluding global ones.
- `MIN_YEAR` — earliest publication year to consider.
- `QUERIES` — the small set of search strings sent to both APIs.

### Automating

Two options if you want this to run without you touching it:

1. **GitHub Actions cron** — add a workflow that runs `paper_watcher.py
   --post` weekly. Requires nothing extra because the endpoint URL is
   already public.
2. **Local Windows task** — Task Scheduler running `python
   _tooling/paper_watcher.py --post` on Mondays.

Neither is set up here yet; do it when the manual cadence gets tiring.

## What the sheet tabs look like now

| tab | who writes | what |
|---|---|---|
| `newsletter` | the site (Newsletter form) | new subscribers |
| `partners` | the site (Sumate form) | partnership inquiries |
| `study-proposals` | the site (Proponer estudio form) | community-suggested papers |
| `paper-candidates` | this script | machine-suggested papers |

The last two feed the same review loop: a human decides which rows
graduate into the `PAPERS` array in `index.html`.
