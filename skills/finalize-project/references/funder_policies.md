# Funder and institutional obligations (SNSF, ERC / Horizon Europe, UZH, Swiss law)

What you *must* do depends on who paid for the paper — read the grant, then
this table. Every row cites the primary source; re-check the source before
relying on a number (policies change; the SNSF's did in 2023 and the Swiss
Human Research Ordinance in 2024). Rows marked *verify* summarise a source
whose full text was not read while writing this; open the link.

## Quick map: obligation → what it means for this checklist

| Obligation | Who | Checklist consequence |
|---|---|---|
| Data underlying the publication in a FAIR repository, **at publication** | SNSF | OpenNeuro snapshot + figshare/Zenodo record must exist when the paper goes online (item 6/7) |
| Data in a *trusted repository*, **at latest by project end**, CC BY/CC0 | ERC | same; CC0 (OpenNeuro) and CC BY (figshare/Zenodo) both fine |
| Repository must give a PID (DOI), public machine-readable metadata, clear licence | SNSF | OpenNeuro, Zenodo, figshare all do |
| SNSF pays data-archiving costs only on **non-commercial** repositories | SNSF | figshare is commercial — usable, but not on the SNSF's bill; a Zenodo copy of the behavioural table is the safe non-commercial mirror |
| Code archived, not just on GitHub | SNSF (explicit), ERC (via DMP "tools needed to reuse") | Zenodo release with DOI (item 8) |
| DMP updated at the end (final DMP with the DOIs) | SNSF, ERC | add a row to the checklist: update DMP in mySNF / Funding & Tenders portal |
| Article **immediately** open access, **CC BY**, no embargo | SNSF (projects submitted ≥ 2023), ERC | choose the OA route with the journal; keep the AAM |
| Deposit every publication in **ZORA** | UZH mandate | deposit VoR/AAM at publication |
| Funding acknowledgement text (SNSF grant number; EU emblem + disclaimer for ERC) | SNSF, ERC | in the paper **and** in the data/code metadata |
| Publicly shared human data must be **anonymised** in the HRA/HRO sense, or covered by consent | Swiss law (HRA/HRO) | defacing + identifier audit (items 6) are the anonymisation; check the consent wording |
| Retain the underlying data (≈10 years is the norm) | UZH/journals; HRA protocol | canonical dataset archived per **data-archival**; never rely on the public copy alone |

## SNSF

**Open Research Data policy** — <https://www.snf.ch/en/dMILj9t4LNk8NwyR/topic/open-research-data>
- Data underlying a publication must be made publicly accessible on a
  FAIR-compliant repository "as soon as their publication is available";
  "all data underlying a publication" plus the documentation needed to
  reproduce (metadata, code). Data not needed for reproducibility is optional.
- If data cannot be shared (justified), the metadata and documentation still go
  to a FAIR repository.
- DMP is part of every grant and must be finalised at project end.
  Content spec: <https://www.snf.ch/media/en/4i9AE5YEIf7tqhGz/DMP_content_mySNF-form_en.pdf>
- Up to **CHF 10,000** for preparing and archiving data — only on
  repositories that "do not serve any commercial purposes".
- GitHub is version control, "not a data archiving tool": archive code (Zenodo
  integration is the SNSF's own example).

**Which repositories qualify** —
<https://www.snf.ch/en/7GhWDP8omTMLZ00O/news/news-210122-open-research-data-which-data-repositories-can-be-used>,
checklist <https://www.snf.ch/media/en/zKRJknEq0OHE5pEQ/Checklist_data_repositories.pdf>,
worked examples (Dryad, EUDAT, Harvard Dataverse, Zenodo; 2017)
<https://www.snf.ch/media/en/k64VoMUfwKoUMMY5/FAIR_data_repositories_examples.pdf>
- Minimum criteria: persistent unique identifier (DOI/ARK); structured,
  machine-readable metadata; metadata public even when data are restricted;
  licence clearly defined; ideally a long-term preservation plan.
- "Other data repositories may also be used, provided that they comply with the
  FAIR data principles" — OpenNeuro qualifies on every criterion (DOI via
  DataCite, public metadata, CC0, validator-enforced metadata).

**Open access** — <https://www.snf.ch/en/MDecEyLJgpSTk0cU/page/open-access-information-for-researchers>,
change notice <https://www.snf.ch/en/33WC4FGNdpfXrqPV/news/immediate-open-access-without-restrictions-changes-as-of-1-january-2023>
- Articles: **CC BY**, **no embargo** (projects submitted before 1 Jan 2023:
  ≤ 6 months). Gold (APC paid by SNSF, not for hybrid/special issues), green
  (AAM in an institutional/disciplinary/generalist repository — ZORA, Zenodo,
  Europe PMC; not ResearchGate) or rights retention.
- Acknowledgement wording: "This research was funded in whole or in part by
  the Swiss National Science Foundation (SNSF) [grant number]."

## ERC / Horizon Europe (Model Grant Agreement, Article 17)

**ERC open-science page** — <https://erc.europa.eu/manage-your-project/open-science>;
annotated grant agreement (Art. 17, Art. 17.2 visibility of funding) —
<https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/common/guidance/aga_en.pdf>;
practical guide — <https://www.openaire.eu/how-to-comply-with-horizon-europe-mandate-for-rdm>
- Publications: deposit in a **trusted repository** "before or at publication
  time", immediate OA, **CC BY** (or equivalent), rights retained by the
  author/institution. APCs eligible only in full-OA venues; hybrid and
  transformative journals are not reimbursed.
- Data: DMP "at the latest at the end of month 6", kept updated; deposit "as
  soon as possible and within the deadlines set out in the DMP" and at the
  latest by project end, in a trusted repository; "as open as possible, as
  closed as necessary" — every restriction justified in the DMP; data under
  **CC BY or CC0** (or equivalent); **metadata under CC0**; FAIR; describe the
  tools/instruments needed to reuse the data (i.e. the code and environment).
- Recommended general repositories: Zenodo (OpenAIRE), figshare, HAL;
  domain: Europe PMC, arXiv. Outputs get linked to the grant via OpenAIRE —
  put the grant number in the Zenodo/figshare metadata (`grants` field).
- *verify*: the EU emblem + "Funded by the European Union (ERC, <acronym>,
  <grant number>). Views and opinions expressed are however those of the
  author(s) only …" disclaimer applies to publications, data records and
  code READMEs — take the exact text from the AGA Art. 17.2.

## UZH

**Open Science Policy (Executive Board, 28 Sept 2021)** —
<https://www.openscience.uzh.ch/en/open-science-at-uzh/open-science-policies/uzh-open-science-policy.html>,
full text DOI <https://doi.org/10.5281/zenodo.10066199>,
announcement <https://www.news.uzh.ch/en/articles/2021/open-science.html>
- Recommendations, not binding rules: "public and free access to scientific
  results and data, codes, teaching materials and publications is a core
  concern"; FAIR data; reproducibility; faculties may add discipline-specific
  requirements (*verify* whether the faculty has).

**ZORA deposit mandate (since 2008)** —
<https://www.ub.uzh.ch/en/wissenschaftlich-arbeiten/publizieren-auf-uzh-plattformen/zora-policy.html>,
funder-requirements overview <https://www.ub.uzh.ch/en/wissenschaftlich-arbeiten/anforderungen-forschungsfoerderer/requirements-oa.html>
- Deposit a copy of every published work in ZORA if no legal objection; file
  embargo ≤ 12 months in justified cases. ZORA is OpenAIRE-compliant, so one
  deposit satisfies UZH, SNSF green road and Horizon Europe "trusted
  repository" at once.

**Research data management** —
<https://www.ub.uzh.ch/en/wissenschaftlich-arbeiten/mit-daten-arbeiten.html>
(Open Science Services, `data@ub.uzh.ch`: DMP support, repository advice,
anonymisation tips); legal/ethical overview —
<https://www.openscience.uzh.ch/en/research-integrity/legal-and-ethical-guidelines.html>;
data protection in research (UZH Legal Services) —
<https://www.rud.uzh.ch/en/angebot/datenschutzrecht/research.html>
- Applicable law: Swiss Federal Act on Data Protection (revised FADP, in force
  1 Sept 2023) <https://www.fedlex.admin.ch/eli/cc/2022/491/en> and the
  cantonal IDG; Human Research Act for health-related data (below).
- Retention: no UZH-wide figure was verified from a primary source while
  writing this; ETH's guideline says ≥ 10 years and swissethics notes journals
  and institutions typically require 10 years (below). Treat **10 years after
  publication** as the floor for the canonical raw data and fits; keep them on
  the institutional archive, not only on the public repositories.

## Swiss law: sharing human data

**Human Research Act (HRA, SR 810.30)** — <https://www.fedlex.admin.ch/eli/cc/2013/617/en>;
**Human Research Ordinance (HRO, SR 810.301)** — <https://www.fedlex.admin.ch/eli/cc/2013/642/en>
- The HRA governs research with health-related **personal** data; **anonymised**
  data fall outside it. HRO Art. 25 (anonymisation): all items which, in
  combination, would allow identification "without disproportionate effort"
  must be **irreversibly** masked or deleted — name, address, date of birth,
  unique identifying numbers explicitly. Amendments in force **1 Nov 2024**
  tighten how anonymisation/coding must be assessed against the state of the
  art (<https://swissethics.ch/en/news/2024/06/06/new-implementing-regulations-apply-as-of-1-november-2024>).
- Consequence: a public dataset is either *anonymised* (defaced, no dates, no
  free text, subject codes unlinkable to the key) — then no further HRA
  consent is required — or it is *coded* data, whose sharing must be covered
  by the consent the participants signed. Read the consent form and the KEK
  protocol before upload; do not promise in `dataset_description.json` an
  approval number you have not checked.
- Framework for the risk-of-re-identification assessment, aligned with
  swissethics: SPHN *Guidance for de-identification of health-related data*
  v2.0 (Feb 2025) —
  <https://sphn.ch/wp-content/uploads/2025/02/Data-de-identification-guidance-v2.0_20250214.pdf>
  (direct vs indirect identifiers, dates → ages/relative times, free text,
  device identifiers, documenting the procedure). `deidentification.md` is the
  imaging-specific application of it.
- Retention under the HRA: no statutory minimum for non-clinical projects; the
  protocol states the duration, and cantonal ethics committees accept > 10
  years only with justification (swissethics leaflet, 2017 —
  <https://swissethics.ch/assets/pos_papiere_leitfaden/merkblatt_datenaufbewahrungsdauer_art34_final_d.pdf>).

## Add to the checklist when a grant applies

1. Funding statement in the paper **and** in every metadata record (Zenodo
   `grants`, figshare "Funding", OpenNeuro `Funding` in
   `dataset_description.json`); ERC: emblem + disclaimer text from the AGA.
2. Final DMP updated with the DOIs (mySNF / EU portal) — SNSF asks for it at
   project end, ERC at each reporting period.
3. AAM/VoR deposited in ZORA at publication (also covers SNSF green road and
   the Horizon Europe trusted-repository requirement).
4. If SNSF money paid for data preparation: the repository must be
   non-commercial — put the behavioural table on Zenodo (or both Zenodo and
   figshare) rather than figshare alone.
5. Consent + protocol wording checked against what is being shared (age/sex,
   defaced MRI, behaviour); decision recorded in the dataset README.
