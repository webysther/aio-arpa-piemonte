# Arpa Piemonte natural-risk products

What Arpa Piemonte publishes beyond the readings of the stations: the alert
bulletin, the per-municipality widget, current danger, vigilance, flood
forecasts, landslide scenarios, snow and avalanches, heat waves, fire danger
and earthquakes, plus the APIs, open data and national sources around them.
It was studied for the
[Arpa Piemonte](https://github.com/webysther/ha-arpa-piemonte) integration, to offer what the
DPC integration offers, for Piedmont, from the regional source. Since 0.2.0,
aioarpapiemonte reads the widget of a municipality, the earthquakes, the heat
waves and the avalanche bulletins of EAWS.

Measured on 2026-11-16 and 17, some again on 18. The numbers are measurements of those days:
measure again, politely, before relying on one. Anything not confirmed is
marked **Unverified**.

Related: [the station files and the api_realtime](arpa-data.md),
[the files of Meteo 3R](https://github.com/webysther/aio-meteo3r/blob/main/docs/meteo3r-data.md),
and [the research notes of the integration](https://github.com/webysther/ha-arpa-piemonte/blob/main/docs/research.md),
with the DPC parity table and the roadmap.

Be polite: a few sequential requests, a generic User-Agent, conditional
requests where the server sends validators. `webgis.arpa.piemonte.it`
refused connections after a few quick requests.

## The products of the website

### Common facts

- **Headers:** Apache sends ETag and Last-Modified, no Cache-Control, and
  `Vary: Accept-Encoding`.
  - A conditional request answers `304`, with either validator (the widget
    of Pray, 2026-11-18).
- **CORS:** `Access-Control-Allow-Methods: *` but no
  `Access-Control-Allow-Origin`. Server-side Python can read the files; a
  browser cannot.
- **Directory listings** answer 403. Only `data/tr/` and `data/sismica/`
  exist under `data/`; `data/allerta`, `frane` and `piene` answer 404.
- **No other CAP feeds:** `export/xmlcap/{vigilanza,piene,frane,valanghe,allerta_domani}.xml`
  answer 404.
- **Snippet pages:** static HTML rebuilt by a job. The data is inline as
  `var data = {...};`, valid JSON that `json.JSONDecoder().raw_decode` reads
  from that point. It depends on the page template, so it can break.
  - **The index** `/rischi_naturali/snippets_arpa/` (58 KB) links about 60
    snippets.
- **Licence:** `/note-legali` puts the site content and open data under CC
  BY 4.0, credited as "Fonte: Arpa Piemonte - www.arpa.piemonte.it". The
  widget JSON also asks to keep Arpa's widget layout, unless only the bell
  icon is used; the heat-wave widget asks to keep its layout, without that
  exception.
- **PDFs:**
  - current bulletins: `/rischi_naturali/boll/bollettino_{allerta,vigilanza,piene,frane,aggiornamento,calore,calore_comune_torino,incendi}.pdf`;
  - archive: `/boll/archivio_bollettini/{kind}/bollettino_YYYY-MM-DD[_HH].pdf`;
  - index: the plain-text `/boll/lista_pdf` (551 KB, 9,037 lines, from
    2023-01-01).

### Summary

| Product | Data URL | Format | Unit | Days | Cadence | Overlaps DPC? | Machine-readable |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Alert bulletin | `/export/xmlcap/allerta.xml`; `/rischi_naturali/snippets_arpa/allerta/` | CAP XML; JSON in HTML | Piem-A..M | today (+0/+12 h) and tomorrow (+12/+36 h) | daily, ~11:30 local (by 13:00) | partly (3 of 5 risks) | yes (CAP); HTML adds numbers |
| Municipality widget | `/rischi_naturali/widget/comuni/{ISTAT6}/index.json` | JSON, ~2.5 KB | municipality | day 0, day 1 | alert daily; danger ~hourly | partly | yes |
| Current danger | `/snippets_arpa/mappa_pericolo/` | JSON in 3 MB HTML | municipality | now (3 h), last 24 h | ~hourly or faster (unverified) | no | scraping JSON |
| Vigilance | `/snippets_arpa/vigilanza/` | JSON in HTML | Piem-A..M | 3 days | daily | no | scraping JSON |
| Flood forecast | `/snippets_arpa/piene/` | JSON in HTML + municipality table | 26 river sections + Lago Maggiore (9-digit id) | +12/24/36 h, trend to 48 h | weekdays 12:00, more in events | no | scraping JSON |
| Landslides | `/snippets_arpa/frane/` | JSON in HTML | zones A–M | last 24 h, today, tomorrow | weekdays 12:00 | no | scraping JSON |
| Snow per sector | `/rischi_naturali/dati_valanghe.json` | JSON, 2 KB | 14 alpine sectors | latest day | daily | no | yes |
| Avalanche bulletin | `https://bollettini.aineva.it/albina_files/latest/IT-21_it_CAAMLv6.json` | CAAMLv6 JSON/XML | 14 EAWS micro-regions IT-21-xx | day + tendency | daily in season (Dec–May) | no | yes (AINEVA) |
| Heat waves | `/rischi_naturali/widget/caldo/{city}/index.json` | JSON, ~2.7 KB | 8 provincial capitals | 3 | daily, 15 May – ~30 Sep | no | yes |
| Fire danger | `/snippets_arpa/incendi_new/map_macro/` | SVG titles in HTML; PDF | 6 macro-areas | 7 | daily | no | SVG scraping only |
| Earthquakes | `/rischi_naturali/data/sismica/sismica_tabella.json` | JSON, 10.4 KB | point | last 30 days | near real time | no | yes |
| PDFs | `/rischi_naturali/boll/…`, `lista_pdf` | PDF / text | — | archive from 2023 | per bulletin | — | links only |

### Alert bulletin, CAP-XML

- **The file:** `https://www.arpa.piemonte.it/export/xmlcap/allerta.xml`,
  `application/xml`, 18,713 B (823 B gzip), ETag + Last-Modified.
  - **Live sample:** bulletin 333/2026, sent 2026-11-16T10:26:25+00:00, all
    green, avalanches BIANCO.
- **Guide:** "Formato CAP-XML per allertamento meteoidrologico piemontese",
  v2.0, 2024-10-03 (`https://www.arpa.piemonte.it/media/5133`). Issued by the
  Centro Funzionale every day by 13:00 local.
- **Header:**
  - `identifier`: the bulletin number ("52/2020");
  - `sender`: centro.funzionale@arpa.piemonte.it;
  - `sent` (UTC) and `status` (Actual; Test in the examples);
  - `msgType`: Alert when any zone has a colour other than green or white,
    otherwise Update;
  - `source` Operator, `scope` Public;
  - `note`: the bulletin note or a technical message.
- **One `<info>` per zone, 11 zones:** Piem-A, B, C, D, E, F, G, H, I, L, M.
  The guide's example starts with an **empty `<info/>`**, which the parser
  must skip.
  - `category`: Geo when any risk is at least yellow, otherwise Met.
  - `event`: the worst colour of `_1224` and `_2436`, one of BIANCO #FFFFFF,
    VERDE #6EBB00, GIALLO #FFFF00, ARANCIONE #FFA500, ROSSO #FF0000.
  - `responseType` (Prepare/None), `urgency` (Expected/Unknown) and
    `certainty` (Likely).
  - `severity`: Extreme (red), Severe (orange), Moderate (yellow), Unknown.
  - `onset` and `expires` in UTC.
  - `instruction`: a link to the operational phase.
  - `parameter`s:
    - `EFFETTI SUL TERRITORIO`: free text, "-" when there is none;
    - `IDRAULICO_*`, `IDROGEOLOGICO_*`, `TEMPORALI_*`, `NEVE_*`,
      `VALANGHE_*`, each with `_1224` (the first 12 h after issue) and
      `_2436` (the next day).
  - `area/areaDesc`: the zone code. There is no geometry or geocode.
- **Values:** BIANCO (not evaluated) / VERDE / GIALLO or GIALLA / ARANCIONE /
  ROSSO or ROSSA. **Both genders appear.**

### Alert snippet

Source: `/snippets_arpa/allerta/`, 698 KB.

- **Codes:** `all_0` green, `all_1` yellow, `all_2` orange, `all_3` red,
  `all_4` white, `all_99` grey (not available).
- **Bulletin keys:** `numero_bollettino`, `data_emissione`, `last_update`
  (local time, no offset), `prossimo_aggiornamento`, `ore_validita` 36,
  `fraserisknat`, `massimo_allerta`.
- **Levels:** `EVENT{Piem-X}`, plus `giorno1` and `giorno2`, each
  `{Piem-X: {EVENT, detail: {IDRAULICO, IDROGEOLOGICO, NEVE, TEMPORALI,
  VALANGHE}}}`.
- **Zones:** `w23_data[11].id_w23_zone{bacino, nome_zona, provincia,
  zona_allerta}`.
- **Numbers:**
  - fresh snow at 400/700/1000 m (`neve400_oggi`…) and snow line (`neveq*`);
  - forecast rain, max and areal mean over 6/12/24/48 h (`pluvmax*`,
    `pluvmed*`); the `_oss` suffix is observed.

### Municipality widget

- **The file:** `/rischi_naturali/widget/comuni/{ISTAT6}/index.json` (Torino
  `001272`), rebuilt at 04:53:37 GMT.
- **Keys:**
  - `allerta` (the maximum) and `{idrogeologico,idraulico,temporali,neve,valanghe}_day_0|_day_1`;
  - `numero_bollettino`, `emesso_il` (with offset), `prossimo_aggiornamento`;
  - `zone_di_allerta` ("Piem-L"; "Piem-G,Piem-L" for Asti);
  - `pericolo_attuale` with `aggiornamento_livello_di_pericolo_attuale`;
  - `fase_operativa_comunale_attuata`: Nessuna / Attenzione / Preallarme /
    Allarme, with its time;
  - colours, legends and icons.
- **Name → ISTAT list:** `/snippets_arpa/widget_comune/` has
  `var comuni = {"AGLIÈ":"001001", …}`, 1,180 entries. The user found the
  widget there; the page links `/widget/comuni/{ISTAT6}/` (iframe) and its
  `index.json`.
- **ISTAT codes, checked 2026-11-17:**
  - **The widget uses the current ISTAT code:** `096048` is Portula (Piem-B);
    Pray is `096050`.
  - **Meteo 3R `municipality_code` and `pie_anag` `municipality_code` are
    current codes too**, with 0 differences over 374 stations. The prefixes
    are: AL 006, AT 005, BI 096, CN 004, NO 003, PV 018, TO 001, VB 103,
    VC 002.
  - So `ISTAT_<municipality_code>` of a station joins the widget directly.
  - **Pitfall:** the 9-digit website id is **not** the current ISTAT code plus
    a number. Pray's id is `002105900`, built on the **old** code 002105 (from
    before the province of Biella existed). Biella (096) and VCO (103)
    stations likely all carry old codes in their website id, and so do
    `pie_anag` `codice_istat_comune` and the flood snippet's
    `codice_istat_comune`. Never derive the municipality from the website id.

### Current danger

Source: `/snippets_arpa/mappa_pericolo/`, 3.06 MB.

- **3 h block:** `pericolo_comuni[1180]` of `{area, comune, sigla_pro,
  data_agg, idro, pluv, storm, pericolo}`.
- **24 h block:** `"01"+ISTAT6 → {comune, sigla_pro, stato}`.
- **Values:** 0–3 for green → red; −1 and −99 mean not available.
- **Time zones are mixed:** `data_emissione` is local, `data_agg` seems UTC.
- **Coverage:** 56 municipalities lie in two zones.
- **Unverified:** the exact cadence.

### Vigilance

Source: `/snippets_arpa/vigilanza/`.

- **Days:** `giorno1..3`, each `{Piem-X: {EVENT: vig_0..4, PIOGGIA,
  description[], icon[] ("vento_2","neve_1","nebbie_1"), quota (snow line,
  m)}}`.
- **Bulletin keys:** `numero_bollettino`, `sintesi_meteo`, `massimo_2g`,
  `icone_2g`, `ore_validita` 36.
- **Icons:** `/rischi_naturali/images/svg/icon/vigilanza/{icon}.svg`.
- **Unverified:** only `vig_0` and `vig_1` were seen live, so the meaning of
  `vig_2..4` is inferred.

### Flood forecast

Source: `/snippets_arpa/piene/`.

- **Bulletin keys:** `data_emissione`, `ora_emissione` 12:00, `validita` 36
  h, `numero_bollettino`, `prossimo_aggiornamento`.
- **Sections:** `giorno1` holds 27 sections ("001_RACCONIGI") with:
  - `codice_istat_comune` + `progr_punto_com`, the same 9-digit id the library
    builds (`parsers.py` 286–287);
  - `corso_acqua`, `denominazione_stazione`, `id_parametro` (PORTATA /
    PORT_FIU / IDRO);
  - thresholds `codice1..3`, current `portata_attesa` and
    `criticita_attesa`;
  - forecasts `prev_crit12h/24h/36h` and `massimo_previsione`;
  - trends `tendenza6hprecedenti` and `tend48h`;
  - the record `valore_massimo_storico` and `data_massimo_storico`.
- **Codes:** A absent, O ordinary, M moderate, E high.
- **Municipalities:** the table `#piene_comuni` has about 546 rows.

### Landslides

Source: `/snippets_arpa/frane/`.

- **Zones:** plain letters A–M.
- **Days:** `giorno0` is the last 24 h (observed), `giorno1` today (12 h),
  `giorno2` tomorrow (12–36 h). Each zone holds `{EVENT: {SLOPS, DEFENSE,
  PROBABILITA}}`:
  - SLOPS is shallow landslides;
  - DEFENSE is debris flows, only in A–F (`nd` in G–M).
- **Codes:** `frane_-` none, `_1` isolated, `_2` not widespread, `_3`
  widespread.
- **Unverified:** only "nessuna" was seen for `PROBABILITA`.
- **Other keys:** `MASSIMI`, `MASSIMID0..2`, `SituazioneSlops`,
  `SituazioneDefense`.

### Snow and avalanches

- **`dati_valanghe.json`:** `{"date", "data":[[sector, Hs2000, Hs2500,
  Hn2000, Hn2500, Hn3_2000, Hn3_2500, date, "01"], …]}` for 14 sectors
  (Lepontine_Nord … Liguri), with ranges ("10-20" cm) or "N/A".
- **Bulletin:** Arpa's own is suspended; AINEVA publishes it.
  - Files: `albina_files/latest/` (open listing, `IT-21_it_CAAMLv6.json` and
    `.xml`, de/en/fr) and the archive
    `albina_files/YYYY-MM-DD/YYYY-MM-DD_IT-21_it_CAAMLv6.json`.
  - Out of season: on 2026-11-17 `latest` had only IT-34.
  - Structure: `bulletins[]` with `regions[].regionID`,
    `dangerRatings[{mainValue: low…very_high, validTimePeriod}]`,
    `avalancheProblems`, `tendency`, `validTime` and `publicationTime`
    (16:00Z the day before).
  - Micro-regions: IT-21-VB-01..03, VC-01, TO-01..05, CN-01..05.
- **Unverified:**
  - whether the 14 EAWS micro-regions match Arpa's 14 snow sectors;
  - AINEVA's licence and caching headers.

### Heat waves

- **The file:** `/rischi_naturali/widget/caldo/{city}/index.json`, for
  alessandria, asti, biella, cuneo, novara, torino, verbania and vercelli.
  - Keys: `emissione`, `prossimo_aggiornamento`, `note`, then `{CITY: {ISO
    date: {livello_disagio 0–3, description, Tmax/Tmin, perceived max/min,
    giorni_consecutivi_caldo}}}` for 3 days.
- **Season:** suspended out of season (`emissione` 2026-09-30); check that
  date to detect stale data.
- **Richer snippet:** `/snippets_arpa/caldo_regione/` has more data, with
  opaque keys; Torino adds `COD_SALUTE`.
- **The 8 cities, fetched on 2026-11-18:** each file has the days under the
  name of its city in capitals (`TORINO`, `VERBANIA`...), 3 days, `note`
  empty and `emissione` 2026-09-30, the last bulletin of the season. The
  numbers are texts ("26"), and the detail of a level is
  `livello_disagio_dettalio` (sic).

### Fire danger

Source: `/snippets_arpa/incendi_new/map_macro/`.

- **Data:** no JSON. There are 7 inline SVG maps (`div#incendi_DD_MM_YYYY`)
  with 6 `<path>` each, titled "Macroarea: N / Denominazione: X / Livello:
  L".
- **Macro-areas:** 1 Cuneo SO, 2 Nord, 3 Torino Nord, 4 Torino Ovest, 5
  SudEst, 6 Cuneo SE. There is no municipality mapping.
- **Unverified:** the names of levels 1–5. The legend is outlined text;
  "molto basso … molto alto" is a guess.

### Earthquakes

Source: `/rischi_naturali/data/sismica/sismica_tabella.json`.

- **The file:** a list of events, 26 at the time, with `ID evento`, `Data e
  ora (UTC)`, `Distretto sismico`, `Latitudine (N)`, `Longitudine (E)`,
  `(km)` (depth), `valore` (magnitude), `tipo` (ML), `dati_elaborati`,
  `tempo_origine`, `time_elab` and `time_upd`.
- **Coverage:** the last 30 days, 6–10°E × 43.5–47°N. ML ≥ 1.0 events appear
  after review; ML ≥ 2.5 appear automatically within minutes.
- **Times:** `Data e ora (UTC)` and `tempo_origine` are "2026-11-17
  06:42:50"; `time_upd` is "2026-11-17, 08:22:09", with a comma, about an
  hour after `time_elab`: local time, probably. aioarpapiemonte reads only
  the time of the event.
- **On 2026-11-18:** 28 events, all ML and `dati_elaborati` "rivisti", the
  newest first.
- **Unverified:** the time zone of `time_upd`, and the `dati_elaborati` of an
  automatic event.

### Municipality → alert zone

1. Per municipality: `zone_di_allerta` in the widget JSON.
2. In bulk: `mappa_pericolo` `pericolo_comuni[].area`, joined to ISTAT
   through the widget_comune list.
3. DPC GeoJSON: a `Comuni` list per zone feature.

### Compared with DPC

- **The overlap:** DPC copies the Piedmont assessment for hydraulic,
  hydrogeological and thunderstorm risks, today and tomorrow. Its GeoJSON
  names zones (e.g. "Toce") without the Piem-X code and is published at
  ~14:44–16:00.
- **What Arpa adds:** snow and avalanche risks, rain and snow numbers,
  current danger per municipality, the municipal operational phase, 3-day
  vigilance, flood forecasts per section and landslide scenarios. It
  publishes about 3 h earlier.

### Other references

- **Brochure** "Rischi naturali – Conoscerli per prevenirli" (©Regione
  Piemonte 2019, reproduction needs authorization: do not copy).
  - Risks: floods, avalanches, weather phenomena, landslides, earthquakes,
    forest fires and heat waves.
  - The alert bulletin comes daily by 13:00, with yellow/orange/red alerts
    and operational phases Attenzione / Preallarme / Allarme.
  - Avalanche bulletins come from AINEVA (scale 1–5).
  - Seismic zones: 44 municipalities in 3S, 365 in 3, 797 in 4.
- **Not opened:** `mappa_pericolo_dettaglio`, `meteo`, `analisi`,
  `precipitazioni_ultime_ore`, `snippets_arpa_fluid/alertdashboard`,
  `snippets_arpa_alpine/radar` and `meteosat`,
  `snippets_arpa_graphs/tabella_livelli_idro` and `tabella_livelli_pluv`, and
  the air-quality snippets.

## APIs, open data and national sources

**Requests:** about 130 sequential requests with a generic User-Agent, beyond
the planned budget. `webgis.arpa.piemonte.it` timed out or refused after a
few quick requests: **throttle that host**.

### Summary

| Source | Auth | Format | Spatial unit | Days | Cadence | ETag/LM | License | Stable machine-readable? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api_realtime `data_pie` / `pie_anag` / `pie_neve` | none | JSON (OpenAPI) | station | 3 d / 7 d (snow) | hourly / daily | no | CC BY 4.0 (Arpa) | **yes** (documented) |
| CAP `export/xmlcap/allerta.xml` | none | CAP 1.2 XML | Piem-A..M | today + tomorrow (12–24, 24–36) | daily ~13:00, plus updates | yes | CC BY 4.0 | **yes** |
| Widget `widget/comuni/{ISTAT6}/index.json` | none | JSON | municipality | day 0/1 + nowcast | ~10 min | yes | CC BY 4.0, cite and keep layout | **yes in practice** (public widget, undocumented schema) |
| `export/meteoxml/meteo.xml` | none | XML | region / sector / district | ~3 d | daily ~12:30 local | yes | CC BY 4.0 | yes |
| `data/sismica/sismica_tabella.json` | none | JSON, 10.4 KB | event | last 30 days | minutes | yes | CC BY 4.0 | yes |
| `data/sismica/sismica_mappa_storico.geojson` | none | GeoJSON, 15 MB, 26,030 events | event | historical catalogue | minutes | yes | CC BY 4.0 | yes, but heavy |
| `boll/*.pdf` + `boll/lista_pdf` | none | PDF + text index | — | archive since 2023 | per bulletin | yes | CC BY 4.0 | links only |
| Embedded JSON on snippet pages (piene, vigilanza, frane, mappa_pericolo, incendi, caldo) | none | HTML + JS | zone / station / municipality / macro-area | 1–7 d | ~10 min | yes | CC BY 4.0 | **no** (scraping) |
| webgis ArcGIS (SIFraP, BDE, SIVA…) | none | Esri JSON / GeoJSON | features | static | irregular | no | Arpa (CC BY) | yes (reference data; throttle) |
| DPC criticality GeoJSON (GitHub) | none | GeoJSON / XML / SHP | 156 national zones | today + tomorrow | daily ~16:00 | yes | CC BY 4.0 | yes (a subset of Arpa) |
| INGV FDSN | none | GeoJSON / text / QuakeML | event | any | real time | max-age=60 | CC BY 4.0 (unverified) | **yes** |
| EAWS CAAMLv6 IT-21 + micro-regions | none | JSON / GeoJSON | 14 micro-regions | 1–2 d | daily, seasonal | yes | regions CC0; bulletin unverified | **yes** (seasonal) |
| DPC seismic classification CSV | none | CSV / XLSX | municipality (ISTAT) | static | yearly | LM only | not stated | yes |
| Regional zone, alert-area and phase datasets | none | metadata only / WMS (timed out) | zone / municipality | — | annual / daily | — | CC BY 4.0 | **no** (no download found) |

### Details beyond the products above

- **Widget JSON:**
  - An unknown ISTAT code answers 404.
  - It refreshes about every 10 min: the current-danger time moved from
    04:50 to 05:01 UTC.
  - Split municipalities: Asti "Piem-G,Piem-L", Pinerolo "Piem-C,Piem-L".
- **Weather forecast:** `https://www.arpa.piemonte.it/export/meteoxml/meteo.xml`.
  - Root `weatherData`, with `synoptic`, then
    `forecast/areas/region|sectors|districts` and `nextUpdate`.
  - Metadata: `/export/meteoxml/metadata/metadata_meteo.xml`.
  - **Unverified:** the detailed structure was not examined.
- **Earthquake catalogue:**
  - Sample: `{"event_id":"261113162102","tempo_origine":"2026-11-13 16:21:29","Distretto_sismico":"Alpi Cozie","Profondità":9.5,"Magnitudo":1.5,"tipo_magnitudo":"ML(Mwa2)"}`.
  - No incremental query: conditional GET only.
- **CAP:** there is no sibling `allerta_comuni.xml` or `aggiornamento.xml`
  either (404).
- **Other PDF names:** `bollettino_traps`, `bollettino_idrosintesi`,
  `bollettino_meteotestuale`, `bollettino_previsione_UVI`, and
  `bollettino_allerta.png`.
  - Archive folders: allerta, vigilanza, piene, frane, traps, aggiornamento,
    incendi_new, caldo_regione, caldo_torino, analisi, meteo, bis, uvi.
  - Allerta, vigilanza and meteo go back to 2023-02-12, frane to 2025-01-02.
- **Flood stations:** the snippet listed 28 stations in this survey (27 in
  the site survey). They join `pie_anag` through `codice_istat_comune` +
  `progr_punto_com` (e.g. 004179700, Racconigi on the Maira).
- **Embedded heat and fire data:**
  - fire levels are also written as JS strings ("1__17/11/2026 macroarea:
    Cuneo SO, livello: ..."), which is fragile;
  - heat uses `COD_COLORE`, `ATMAX`, `ATMIN` and `TERMA`, keyed by
    undecoded area codes.
  - `valanghe/` is stale (2024) and only points to the AINEVA image.
- **webgis ArcGIS:** `/ags/rest/services` (legacy) and `/server/rest/services`
  (ArcGIS 11.5).
  - `maxRecordCount` 2000; output JSON, GeoJSON or PBF; native EPSG:32632.
  - The `rischi_naturali` folder holds:
    - `SIFraP_SI_Frane_Piemonte`, the landslide inventory: 5,314 points, e.g.
      `{"idfrana":10000600,"tipologia":"Crollo/Ribaltamento","attivita":"Quiescente"}`;
    - `Banca_dati_eventi`, `BDGeo100` and `Evento_alluvionale_1968…2025`;
    - `SIVA` and `SIVA_catasto` (avalanches), `suscettibilita_*`,
      `PSInSAR`/`SqueeSAR`, `ReRCoMF` and `incendi_modis_fires`.
  - `Info_bollettini/MapServer` only holds suspension messages.
  - It has no live alert or zone layer: everything is reference or static
    data.
- **Regione Piemonte open data:**
  - `dati.piemonte.it` is not CKAN (`/api/3/action/*` 404). It is a Vue app
    over a PHP API (`POST /api/datasets/search`), whose body format is
    undocumented (a guess got 400). Downloads go through
    `api.smartdatanet.it`.
  - The national CKAN `https://www.dati.gov.it/opendata/api/3/action/package_search`
    works and harvests these records, all CC BY 4.0, none with a downloadable
    resource:
    - `zone-allertamento-bollettini-arpa-piemonte` (links only to an old
      page);
    - `arpa-piemonte-aree-e-sottoaree-di-allerta` (no resource; GeoNetwork
      empty);
    - `fasi-operative-piani-di-protezione-civile-regione-piemonte` (WMS
      `https://presidi.serviziprotciv.regione.piemonte.it/ms/wms_fase_operativa?`,
      GetCapabilities timed out after 40 s);
    - the Comune di Torino's monthly criticality datasets for 2007–2018.
- **DPC criticality** (`pcm-dpc/DPC-Bollettini-Criticita-Idrogeologica-Idraulica`):
  - CC BY 4.0, daily ~16:00, `files/{geojson,topojson,shp,xml,pdf}/YYYYMMDD_HHMM_{today,tomorrow}.json`;
  - ~5.5 MB per file; raw GitHub sends ETag and `max-age=300`;
  - it lacks Piem-X codes, ISTAT codes, snow and avalanches, the 12–24 /
    24–36 h windows, and the Arpa-only products. It adds zone geometry.
- **ISTAT → Piem-A..M:** there is no downloadable official list; the 2018
  regional resolution is a PDF
  (`/export/sites/default/pubblicazioni/pdf/dgr_07320_1050_30072018.pdf`).
  - **Not one to one:** 56 of 1,180 municipalities are in two zones (Asti,
    Pinerolo, Novi Ligure, Busca, Giaveno…).
  - **Recommended:** ship a static table built once by joining
    `mappa_pericolo` `pericolo_comuni` with the `widget_comune` name → ISTAT6
    list. All 56 split municipalities matched. Check it against the widget
    JSON, and read the widget live for the configured municipality.
- **Earthquakes, INGV FDSN:**
  - Query: `https://webservices.ingv.it/fdsnws/event/1/query?starttime=…&minlat=44.05&maxlat=46.47&minlon=6.62&maxlon=9.22&minmag=1.5&orderby=time&format=geojson`.
  - No auth; CORS `*`; `max-age=60`; WADL v1.109.0. `geojson` works,
    although the WADL lists only xml and text.
  - Parameters include `latitude`, `longitude`, `maxradiuskm`,
    `minmagnitude`, `limit`, `eventid` and `updatedafter`.
  - Sample: `{"eventId":47951552,"time":"2026-11-16T04:22:58.79","magType":"ML","mag":1.6,"place":"14 km NE Courmayeur (AO)"}`.
  - A bounding box also catches Aosta Valley and border events: filter with
    the Piedmont polygon.
- **Avalanches, EAWS:**
  - Bulletin: `https://static.avalanche.report/eaws_bulletins/{date}/{date}-IT-21.json`
    (CAAMLv6, provider "AINEVA Piemonte"). CORS `*`, ETag and Last-Modified;
    `304` to `If-None-Match` (2026-11-18). The texts are in English
    (`lang` "en").
  - **The names of the bulletin are stale:** the bulletin of 2026-04-18
    names its micro-regions as before 2022-03-04, when they were numbered
    otherwise ("IT-21-TO-03": "Alpi Graie", now IT-21-TO-04), and names
    IT-21-TO-05, new, by its identifier. Its identifiers are the current
    ones: it has the 14 of them. The current names are in
    `https://regions.avalanches.org/micro-regions_names/it.json`
    (IT-21-TO-03 "Alte Valli Susa e Chisone", with Bardonecchia and
    Sestriere, checked with shapely).
    Seasonal: 404 on 2026-11-17. Sample from 2026-04-18:
    `dangerRatings:[{"mainValue":"moderate","elevation":{"lowerBound":"2600"},"validTimePeriod":"earlier"}]`.
  - Micro-regions: `https://regions.avalanches.org/micro-regions/IT-21_micro-regions.geojson.json`,
    CC0 (GitLab eaws/eaws-regions), 27 features. Keep those with
    `end_date` null. `max-age=600`, ETag.
  - **The two surveys disagree:** one found CAAML for IT-21 in the
    `bollettini.aineva.it/albina_files/2026-02-15/` archive; the other found
    no file in `albina_files/latest/` (only IT-34 out of season). Check in
    season.
- **Fire danger:** a PDF (6 macro-areas, today plus 3 days), the embedded
  7-day levels, and the `incendi_new` archive. The "stato di massima
  pericolosità" is declared by regional decree (PDF). No JSON, no open data.
- **Seismic classification:** DPC CSV
  `https://rischi.protezionecivile.gov.it/static/4717c6a369cdc298b69730c9d740e39a/classificazione-sismica-aggiornata-maggio-2025.csv`.
  - `;`-separated, UTF-8 with BOM.
  - Header `REGIONE;PROV_CITTA_METROPOLITANA;SIGLA_PROV;COMUNE;COD_ISTAT_COMUNE;ZONA_SISMICA`;
    e.g. `Piemonte;Torino;TO;Ala di Stura;1003;3S`. The ISTAT code is an
    integer: pad it to 6 digits.
  - 1,182 Piemonte rows; Last-Modified 2026-09-02, `no-store`; also XLSX.
  - No licence stated.
  - Regione Piemonte has only a PDF (DGR 6-887/2019).

### Assessment

- **Primary sources:**
  - the api_realtime, plus `pie_neve`;
  - CAP for zone alerts;
  - the widget JSON for the municipality: the only machine-readable source of
    current danger, of the municipal phase and of multi-zone membership;
  - INGV for earthquakes;
  - EAWS for avalanches;
  - the DPC CSV for the seismic class.
- **Static data to ship:** the ISTAT → zones table, and the EAWS
  micro-regions.
- **Optional:** the embedded page JSON (piene, vigilanza, frane, fire, heat),
  because its schema can change with any rebuild.
- **PDFs:** links only.

### Sources consulted

- CAP spec page: https://www.arpa.piemonte.it/media/5133
- Bulletins index: https://www.arpa.piemonte.it/bollettini
- Fire bulletin guide: https://www.arpa.piemonte.it/bollettini/elenco-bollettini-1/guida_boll_incendi.pdf/view
- INSPIRE zone record: https://inspire-geoportal.ec.europa.eu/srv/api/records/r_piemon:83f043bd-3aad-453d-9637-3fed1cc19420
- EAWS IT-21 sample: https://static.avalanche.report/eaws_bulletins/2026-04-18/2026-04-18-IT-21.json
- Regione seismic classification: https://www.regione.piemonte.it/web/temi/protezione-civile-difesa-suolo-opere-pubbliche/prevenzione-rischio-sismico/classificazione-sismica
- DPC seismic classification: https://rischi.protezionecivile.gov.it/it/sismico/attivita/classificazione-sismica

## Still unverified

- The cadence of the current danger (about 10 minutes from the widget, not
  confirmed on `mappa_pericolo`).
- The meaning of vigilance `vig_2..4` (only `vig_0` and `vig_1` were seen)
  and the values of landslide `PROBABILITA` other than "nessuna".
- The names of the fire danger levels 1–5 (the legend is outlined text).
- The time zone of `time_upd` in `sismica_tabella.json`, and the
  `dati_elaborati` of an automatic earthquake.
- AINEVA: the licence of the bulletins; which host carries the IT-21
  CAAML in season (`bollettini.aineva.it/albina_files` or
  `static.avalanche.report/eaws_bulletins`); whether the 14 EAWS
  micro-regions match Arpa's 14 snow sectors.
- The flood snippet listed 27 sections in one survey and 28 in the other.
- The structure of `export/meteoxml/meteo.xml` and its metadata file.
- The search API body of `dati.piemonte.it`, and the regional
  operational-phase WMS, which timed out.
- Licences: INGV (CC BY 4.0 assumed); the DPC seismic CSV states none.
- Snippets not opened: `mappa_pericolo_dettaglio`, `meteo`, `analisi`,
  `precipitazioni_ultime_ore`, `snippets_arpa_fluid/alertdashboard`,
  `snippets_arpa_alpine/radar` and `meteosat`,
  `snippets_arpa_graphs/tabella_livelli_idro` and `tabella_livelli_pluv`, and
  the air-quality snippets.
