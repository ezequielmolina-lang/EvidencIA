/**
 * EvidencIA — data-collection endpoint
 *
 * Single Apps Script project that:
 *   1. Creates ONE Google Sheet with two tabs (newsletter, partners) on first run
 *   2. Exposes a POST endpoint that appends form submissions to the right tab
 *
 * DEPLOY (once, ~5 minutes):
 *   1. Go to https://script.google.com/ → New project
 *   2. Paste this whole file into Code.gs
 *   3. Run the setup() function once (Extensions → Apps Script → select setup → Run).
 *      Grant permissions. Copy the Sheet URL printed in the Logger.
 *   4. Deploy → New deployment → type: Web app
 *      - Execute as: Me (your account)
 *      - Who has access: Anyone
 *      - Copy the /exec URL that ends with /exec
 *   5. Paste that URL into DATA_ENDPOINT at the top of index.html (in the CONFIG block)
 *   6. Push. Submissions from the live site will now land in the sheet.
 *
 * TO ADD NEW COLUMNS:
 *   Edit the appendRow(...) list for the relevant tab in doPost() and add the
 *   matching header in setup(). Re-run setup() to add missing tabs/headers.
 *
 * TO ROTATE: create a new deployment; old URL keeps working until you delete it.
 */

// If set, bind to this existing sheet by ID. Leave empty ('') to have setup()
// create a brand-new sheet on first run. For redevidencia.org this is the
// user-owned sheet at docs.google.com/spreadsheets/d/<SHEET_ID>/edit
const SHEET_ID = '1OWsEqeoNlTmjYOCzeNqDqscGhxDGOEkHOkkHUK8bJpA';

const SHEET_TITLE = 'EvidencIA — data collection';

const NEWSLETTER_HEADERS = [
  'Timestamp', 'Name', 'Email', 'Role', 'Country', 'Preferred language',
  'Page language', 'Source', 'User agent'
];
const PARTNERS_HEADERS = [
  'Timestamp', 'Name', 'Role', 'Email', 'Country', 'Institution',
  'Interests', 'Message', 'Page language', 'Source', 'User agent'
];
// study-proposals: what the site's 'Proponer estudio' form submits.
const STUDY_PROPOSALS_HEADERS = [
  'Timestamp', 'Name', 'Email', 'Paper URL', 'Paper title',
  'Authors / institution / country', 'Why it belongs',
  'Page language', 'Source', 'User agent', 'Reviewed', 'Decision', 'Notes'
];
// paper-candidates: what the _tooling/paper_watcher.py script POSTs weekly.
const PAPER_CANDIDATES_HEADERS = [
  'Timestamp', 'Fetched at', 'Source', 'Query', 'Title', 'Authors',
  'Year', 'Venue', 'URL', 'DOI', 'Abstract',
  'Rigor score', 'LAC bonus', 'Total score', 'Reviewed', 'Decision', 'Notes'
];

/**
 * Run once from the editor. Creates the sheet (if not already) and adds/fixes
 * the two tabs. Idempotent — safe to re-run.
 */
function setup() {
  const props = PropertiesService.getScriptProperties();
  let sid = SHEET_ID || props.getProperty('SHEET_ID');
  let ss;
  if (sid) {
    try { ss = SpreadsheetApp.openById(sid); } catch (e) { ss = null; }
  }
  if (!ss) {
    ss = SpreadsheetApp.create(SHEET_TITLE);
    sid = ss.getId();
  }
  props.setProperty('SHEET_ID', sid);
  ensureTab_(ss, 'newsletter',        NEWSLETTER_HEADERS);
  ensureTab_(ss, 'partners',          PARTNERS_HEADERS);
  ensureTab_(ss, 'study-proposals',   STUDY_PROPOSALS_HEADERS);
  ensureTab_(ss, 'paper-candidates',  PAPER_CANDIDATES_HEADERS);
  // Drop the auto-created Sheet1 if it's empty
  const s1 = ss.getSheetByName('Sheet1');
  if (s1 && s1.getLastRow() === 0 && ss.getSheets().length > 1) ss.deleteSheet(s1);
  Logger.log('Sheet URL: ' + ss.getUrl());
  Logger.log('Sheet ID:  ' + sid);
  return { url: ss.getUrl(), id: sid };
}

function ensureTab_(ss, name, headers) {
  let s = ss.getSheetByName(name);
  if (!s) s = ss.insertSheet(name);
  if (s.getLastRow() === 0) {
    s.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold');
    s.setFrozenRows(1);
    s.autoResizeColumns(1, headers.length);
  }
  return s;
}

/**
 * POST endpoint. Expects a JSON body with a `type` field ('newsletter' | 'partner')
 * and the form fields. Content-type from the frontend is text/plain (to avoid
 * CORS preflight against script.google.com), so we JSON.parse the raw contents.
 */
function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return json_({ ok: false, error: 'empty body' });
    }
    const payload = JSON.parse(e.postData.contents);
    const props = PropertiesService.getScriptProperties();
    const sid = SHEET_ID || props.getProperty('SHEET_ID');
    if (!sid) return json_({ ok: false, error: 'run setup() first' });
    const ss = SpreadsheetApp.openById(sid);
    const ts = new Date();
    const pageLang = payload.pageLang || '';
    const source   = payload.source   || 'evidencia landing page';
    const ua       = payload.userAgent || '';

    if (payload.type === 'newsletter') {
      ss.getSheetByName('newsletter').appendRow([
        ts, payload.name || '', payload.email || '', payload.role || '',
        payload.country || '', payload.lang || '',
        pageLang, source, ua
      ]);
    } else if (payload.type === 'partner') {
      const interests = Array.isArray(payload.interest)
        ? payload.interest.join(', ')
        : (payload.interest || '');
      ss.getSheetByName('partners').appendRow([
        ts, payload.name || '', payload.role || '', payload.email || '',
        payload.country || '', payload.institution || '',
        interests, payload.message || '',
        pageLang, source, ua
      ]);
    } else if (payload.type === 'study-proposal') {
      ss.getSheetByName('study-proposals').appendRow([
        ts, payload.name || '', payload.email || '',
        payload.url || '', payload.title || '',
        payload.authors || '', payload.reason || '',
        pageLang, source, ua,
        '', '', ''  // Reviewed / Decision / Notes — filled in by hand
      ]);
    } else if (payload.type === 'paper-candidate') {
      ss.getSheetByName('paper-candidates').appendRow([
        ts,
        payload.fetchedAt || '',
        payload.source || '',
        payload.query || '',
        payload.title || '',
        payload.authors || '',
        payload.year || '',
        payload.venue || '',
        payload.url || '',
        payload.doi || '',
        payload.abstract || '',
        payload.rigorScore == null ? '' : payload.rigorScore,
        payload.lacBonus == null ? '' : payload.lacBonus,
        payload.totalScore == null ? '' : payload.totalScore,
        '', '', ''  // Reviewed / Decision / Notes
      ]);
    } else {
      return json_({ ok: false, error: 'unknown type: ' + payload.type });
    }
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  }
}

/**
 * GET endpoint:
 *   - /exec?check=1  → JSON with row counts (and last row) per tab, so we can
 *                      verify writes are landing without opening the sheet
 *   - /exec (bare)   → friendly text so opening in a browser isn't confusing
 */
function doGet(e) {
  const params = (e && e.parameter) || {};
  if (params.check === '1' || params.check === 'true') {
    try {
      const sid = SHEET_ID || PropertiesService.getScriptProperties().getProperty('SHEET_ID');
      if (!sid) return json_({ ok: false, error: 'run setup() first' });
      const ss = SpreadsheetApp.openById(sid);
      const tabs = ['newsletter', 'partners', 'study-proposals', 'paper-candidates'];
      const out = {};
      tabs.forEach(name => {
        const s = ss.getSheetByName(name);
        if (!s) { out[name] = { exists: false }; return; }
        const last = s.getLastRow();
        const dataRows = Math.max(0, last - 1); // minus header
        let lastRow = null;
        if (last >= 2) {
          const width = s.getLastColumn();
          lastRow = s.getRange(last, 1, 1, width).getValues()[0].map(v => {
            if (v instanceof Date) return v.toISOString();
            const s = String(v);
            return s.length > 120 ? s.slice(0, 120) + '…' : s;
          });
        }
        out[name] = { rows: dataRows, lastRow };
      });
      return json_({ ok: true, sheet: sid, tabs: out });
    } catch (err) {
      return json_({ ok: false, error: String(err) });
    }
  }
  return ContentService
    .createTextOutput('EvidencIA data-collection endpoint. Use POST with a JSON body.')
    .setMimeType(ContentService.MimeType.TEXT);
}

function json_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}
