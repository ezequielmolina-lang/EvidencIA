# EvidencIA — Landing Page

Single-file, trilingual (ES / EN / PT) landing page for the Latin American network on AI and learning science, plus a Google Apps Script that captures form submissions to a Google Sheet.

## Files

- `index.html` — the whole site: HTML, inline CSS, inline JS, ES/EN/PT content, papers grid, form handlers.
- `apps_script/datasheet.gs` — Google Apps Script Web App that receives POSTs from the forms and appends them to a Google Sheet with `newsletter` and `partners` tabs.
- `README.md` — this file.

No build step, no local dependencies. Fonts (Source Serif 4 + Inter) load from Google Fonts.

## Run locally

```bash
python -m http.server 9886 --directory EvidencIA
# open http://localhost:9886/
```

## Language switching

- Default language: detected from `navigator.language`, falls back to Spanish.
- Selection is persisted in `localStorage` (`evidencia-lang`).
- ES / EN / PT toggle in the header updates every element tagged with `data-i18n`.
- Portuguese is a working machine-drafted translation — worth a review by IA.Edu Brasil before launch.

## Data collection — 5-minute setup

Both forms POST to a single Google Apps Script Web App that writes to a Google Sheet with two tabs.

### 1. Create the Apps Script project

1. Open <https://script.google.com/> and click **New project**.
2. Delete the boilerplate in `Code.gs` and paste the contents of [`apps_script/datasheet.gs`](apps_script/datasheet.gs).
3. Rename the project to `EvidencIA — data collection`.

### 2. Run `setup()` once

1. In the editor's function dropdown, select `setup`.
2. Click **Run**. Grant the permissions Google asks for.
3. Open the **Execution log** — you'll see the URL and ID of the sheet the script just created (or reused, if it already existed).
4. Open the sheet to confirm the `newsletter` and `partners` tabs exist with headers.

### 3. Deploy as a Web App

1. Click **Deploy → New deployment**.
2. Select type **Web app**.
3. Configuration:
   - **Description**: `EvidencIA data collection v1`
   - **Execute as**: **Me** (your Google account — the sheet owner)
   - **Who has access**: **Anyone**
4. Click **Deploy** and copy the **Web app URL** (it ends in `/exec`).

### 4. Wire the page

In [`index.html`](index.html), find the CONFIG block near the top of `<script>` and paste your `/exec` URL:

```js
const CONTACT_EMAIL = 'hola@evidencia.ai'; // TODO
const DATA_ENDPOINT = 'https://script.google.com/macros/s/AKfycb.../exec';
```

Push. Every submission from the live site lands in the sheet.

### If you ever change the Apps Script

Re-deploy: **Deploy → Manage deployments → Edit → New version → Deploy**. The `/exec` URL stays the same across versions.

### If you want to rotate the URL

**Deploy → New deployment** — this issues a new `/exec` URL. Update `DATA_ENDPOINT`. Old deployment keeps working until you archive it under **Manage deployments**.

### Fallback

If `DATA_ENDPOINT` is empty, both forms open a pre-filled `mailto:` draft to `CONTACT_EMAIL` — nothing is silently lost while the sheet is being set up.

## What lands in the sheet

**`newsletter` tab** — one row per signup:
Timestamp · Name · Email · Role · Country · Preferred language · Page language · Source · User agent

**`partners` tab** — one row per inquiry:
Timestamp · Name · Role · Email · Country · Institution · Interests · Message · Page language · Source · User agent

`Interests` is a comma-separated list from the checkboxes (co-lead / speaker / research / policy / info).

## Deployment

The site is static — deploys anywhere. To follow the `capacitacion-docentes` → `eligiendomicamino.org` pattern with a custom domain:

1. Push to GitHub (already done: [ezequielmolina-lang/EvidencIA](https://github.com/ezequielmolina-lang/EvidencIA)).
2. GitHub Pages is enabled from `main` root. Live at <https://ezequielmolina-lang.github.io/EvidencIA/>.
3. When a domain is decided, add a `CNAME` file at the repo root with the domain, and point the DNS at GitHub Pages.

## Content sources

| Section | Source |
|---|---|
| Hero, problem framing, products, founding partners, invitation | `EvidencIA_Invitacion.docx`, `EvidencIA_Overview_EN.docx` |
| Newsletter preview card | `EvidencIA_Newsletter_Propuesta.docx` (Edition #1) |
| Smackdowns (4 sample questions) | `EvidencIA_Smackdowns_12.docx` (full 12 available if we ever commit to them) |
| Willingham epigraph | Newsletter proposal, Edition #1 |
| Base de evidencia — 8-paper WB AI series | `WB_downloads_data.json` (refreshed every 2 months by the `wb-downloads-dashboard` pipeline) |

## Before launch — checklist

- [ ] Replace `CONTACT_EMAIL` placeholder
- [ ] Run the Apps Script setup + deploy + paste `DATA_ENDPOINT`
- [ ] Native-speaker review of PT translations
- [ ] Confirm partner roster on the page vs the real founding-partners list
- [ ] Decide domain, add `CNAME`, update `<meta property="og:url">`
- [ ] Add an OG image once the visual identity is locked
- [ ] Refresh the 8-paper URLs if the WB dashboard data changes materially
