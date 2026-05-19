# EvidencIA — Landing Page

Single-file, trilingual (ES / EN / PT) landing page for EvidencIA, the Latin American network on AI and learning science. Built from the three source documents (`EvidencIA_Invitacion`, `EvidencIA_Newsletter_Propuesta`, `EvidencIA_Overview_EN`).

## Run locally

```bash
# from C:\Users\cosmo\Downloads
python -m http.server 9876
# open http://localhost:9876/EvidencIA/
```

Already wired into the running `cert-page` preview server (port 9876, cwd `C:\Users\cosmo\Downloads`): open `/EvidencIA/`.

## Files

- `index.html` — everything is here: HTML structure, inline CSS, inline JS, full ES/EN/PT content dictionaries.
- `README.md` — this file.

No build step. No dependencies installed locally. Google Fonts (Fraunces + Inter) load from CDN.

## Language switching

- Default language: detected from `navigator.language`, falling back to Spanish.
- User selection is persisted in `localStorage` (`evidencia-lang`).
- ES / EN / PT toggle is in the top-right of the header and updates every element with a `data-i18n` attribute.
- Portuguese is a working draft translation — recommend a quick review by IA.Edu Brasil before launch.

## Forms — wiring instructions

Both forms (newsletter + partner inquiry) are scaffolded for the same Google Forms POST pattern used in `capacitacion-docentes`. Until URLs are set, both forms fall back to opening a pre-filled `mailto:` draft so no submissions are lost.

### To wire up a form

1. Create a Google Form with the fields below.
2. Open the form's `viewform` page source, search for `FB_PUBLIC_LOAD_DATA_`, and grab:
   - The `formResponse` URL — looks like `https://docs.google.com/forms/d/e/<FORM_ID>/formResponse`
   - The numeric `entry.XXXXXXX` ID for each field
3. Paste them into the CONFIG block at the top of `<script>` in `index.html`:

```js
const NEWSLETTER_FORM = {
  action: 'https://docs.google.com/forms/d/e/<FORM_ID>/formResponse',
  fields: {
    name:    'entry.XXXX',
    email:   'entry.XXXX',
    role:    'entry.XXXX',
    country: 'entry.XXXX',
    lang:    'entry.XXXX',
  }
};
```

### Field list — newsletter form
| Form field | Type | Required |
|---|---|---|
| name | short text | yes |
| email | short text (validate email) | yes |
| role | dropdown (docente, admin, ministerio, investigador, edtech, otro) | no |
| country | short text | no |
| lang | dropdown (es, pt, en) | no |

### Field list — partner inquiry form
| Form field | Type | Required |
|---|---|---|
| name | short text | yes |
| role | short text | yes |
| email | short text (validate email) | yes |
| country | short text | yes |
| institution | short text | yes |
| interest | checkboxes (co-lead, speaker, research, policy, info) | no |
| message | paragraph | no |

Also update `CONTACT_EMAIL` at the top of the script — currently a placeholder `hola@evidencia.ai`.

## Deployment

The page is fully static and can deploy anywhere. To follow the `capacitacion-docentes` → `eligiendomicamino.org` pattern:

1. Push `EvidencIA/` (or its contents) to a GitHub repo.
2. Enable GitHub Pages on the relevant branch.
3. Add a `CNAME` file with the target domain (e.g. `evidencia.ai`, `evidencia.org`, etc.).
4. Point the domain's DNS to GitHub Pages.

## Content sources

| Section | Source doc |
|---|---|
| Hero, problem framing, products, founding partners, invitation | `EvidencIA_Invitacion.docx`, `EvidencIA_Overview_EN.docx` |
| Newsletter preview card, "Three rotating sections" | `EvidencIA_Newsletter_Propuesta.docx` (Edition #1) |
| 12 Smackdown questions + SÍ/NO arguments per debate | `EvidencIA_Smackdowns_12.docx` |
| Evidence numbers (Harvard 2×, Nigeria +0.31SD, Stanford $20, Ecuador +0.28SD, Bastani −17%, Gerlich, Benedek) | `EvidencIA_Invitacion.docx`, `EvidencIA_Newsletter_Propuesta.docx` |
| Willingham epigraph | `EvidencIA_Newsletter_Propuesta.docx` (Edition #1, Pensamiento Final) |

## Known checks before launch

- [ ] Replace `CONTACT_EMAIL` placeholder
- [ ] Wire both Google Forms (action URL + entry IDs)
- [ ] Native-speaker review of PT translations (esp. the 96 Smackdown arguments — drafted by me)
- [ ] Add a 4th newsletter sample edition if "Egresados universitarios: Alerta temprana de la crisis del empleo" gets unlocked (Google Doc was not fetchable)
- [ ] Confirm partner roster — currently lists World Bank, MetaRed Global, Anthropic, IA.Edu Brasil, UPC, UCR (from the EN overview; the Spanish invitation lists only WB + UPC)
- [ ] Decide final domain + canonical URL for `<meta property="og:url">` (not yet set)
- [ ] Add a real OG image once the visual identity is locked in
