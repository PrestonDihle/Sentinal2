# PIR 1: Instability Drivers in the Greater Middle East

**Classification:** UNCLASSIFIED // OPEN SOURCE ONLY

**PIR Question:** What specific factors are driving instability in the Greater Middle East, and do these factors indicate a shift toward armed conflict? This PIR focuses on identifying catalysts of instability and the transition from gray-zone activity to kinetic engagement.

---

## Indicator 1.1: Mobilization or Repositioning of Iranian-Aligned Militia Groups (IAMGs) in Iraq and Syria

**Purpose:** Detects forward positioning of IAMG capabilities as a leading indicator of imminent or planned kinetic activity.

### SIR 1.1.1
**Requirement:** Detect movement of heavy weapons systems or rocket and missile components between established storage sites and known launch positions in eastern Syria (Deir ez-Zor, Abu Kamal) and western Iraq (Al-Qaim, Al-Anbar province).

**Collection Method:** Satellite imagery change detection; thermal anomaly monitoring; cross-referencing with geolocated incident reporting.

**Primary Sources:**
- Sentinel Hub EO Browser (apps.sentinel-hub.com/eo-browser) -- Copernicus Sentinel-1 SAR and Sentinel-2 optical; free; 5-day revisit; all-weather SAR detects vehicle concentrations and cleared pad areas
- NASA FIRMS (firms.modaps.eosdis.nasa.gov/map) -- near-real-time thermal anomalies; 10-minute VIIRS updates; detects launch site preparation and post-launch burn signatures
- ACLED Syria and Iraq (acleddata.com) -- geolocated SIGACT database; filter by IAMG-affiliated actor groups; exportable; treat as B-rating for geolocation and timing
- Bellingcat (bellingcat.com) -- open-source geolocation verification; publishes imagery analysis within 24-48 hours of significant events
- SOHR (syriahr.com/en) -- Syrian Observatory for Human Rights; raw incident data for eastern Syria; cross-reference for corroboration

### SIR 1.1.2
**Requirement:** Report anomalous blackout periods or significant changes in public media output frequency from known IAMG Telegram channels, official websites, and affiliated press agencies that deviate from established posting baselines. Sudden silence or output suppression may indicate emissions control (EMCON) posture or leadership dispersion ahead of operations.

**Collection Method:** Social media monitoring of publicly accessible IAMG-affiliated platforms; Telegram channel analytics; baseline comparison against documented posting frequency.

**Primary Sources:**
- tgstat.com -- Telegram analytics; tracks posting frequency, subscriber-to-view ratio anomalies, and channel growth spikes for known IAMG-affiliated channels (Kata'ib Hezbollah, Islamic Resistance in Iraq, PMF-affiliated outlets)
- Telemetr.io (telemetr.io) -- Telegram channel metrics; cross-reference subscriber and message volume changes against historical baseline
- Iraqi PMF Official Media (pmu.gov.iq) -- official Popular Mobilization Forces communications; use as baseline posting frequency reference for comparison
- Al Mayadeen (english.almayadeen.net) -- Resistance Axis platform; monitoring output frequency here reflects Iran-aligned network communication posture
- X Advanced Search (twitter.com/search-advanced) -- monitor known IAMG spokesperson accounts for posting gaps or sudden shifts in messaging tone and volume

### SIR 1.1.3
**Requirement:** Report sudden evacuation of non-essential personnel or civilian family members from militia-controlled compounds in eastern Syria.

**Collection Method:** Satellite imagery analysis; regional news monitoring; IOM displacement tracking; cross-referencing multiple independent sources.

**Primary Sources:**
- Syria Direct (syriadirect.org) -- Amman-based; strong field reporting on eastern Syria; covers population movement near militia compounds
- SOHR (syriahr.com/en) -- raw incident reporting; compound activity changes in Syrian IAMG-controlled areas
- Sentinel Hub EO Browser (apps.sentinel-hub.com/eo-browser) -- imagery cross-check for sudden vehicle concentrations or compound clearing activity near militia facilities
- IOM Displacement Tracking Matrix (dtm.iom.int) -- IOM population movement surveys; Syria section tracks sub-district level displacement spikes
- Shafaq News (shafaq.com/en) -- Erbil-based; covers Iraq-Syria border security incidents including movement of IAMG-affiliated populations

---

## Indicator 1.2: Escalation in State-Sponsored Cyber Activity Targeting Regional Critical Infrastructure

**Purpose:** State-sponsored cyber operations against energy and water infrastructure are a documented precursor to or accompaniment of kinetic escalation in this theater.

### SIR 1.2.1
**Requirement:** Monitor for publicly reported anomalies, service disruptions, or disclosed cyber incidents targeting Israeli or Gulf Cooperation Council (GCC) energy, water, or desalination infrastructure, corroborated by national cybersecurity authority advisories or ICS-specific threat intelligence disclosures.

**Collection Method:** Monitor ICS/SCADA-specific threat disclosures from national CERTs and cybersecurity vendors; cross-reference with regional news reporting on unexplained infrastructure outages.

**Primary Sources:**
- CISA ICS Advisories (cisa.gov/ics-advisories) -- US ICS/SCADA threat advisories; frequently reference Iranian-attributed activity against Israeli and GCC critical infrastructure
- Israeli National Cyber Directorate (INCD) -- gov.il/en/departments/national-cyber-directorate; official Israeli public alerts on critical infrastructure targeting
- Claroty Team82 (claroty.com/team82) -- ICS/OT-specific threat intelligence; publishes free reports on industrial control system threats
- Dragos Year in Review (dragos.com/resources) -- annual ICS threat landscape report; Iran attribution patterns in MENA region; free download
- Check Point Research (research.checkpoint.com) -- Israeli-based; frequently first publisher on Iran-attributed cyberattacks in the region
- UK NCSC (ncsc.gov.uk/news) -- publishes attribution statements on state-sponsored cyber activity; cross-reference for UK government assessment

### SIR 1.2.2
**Requirement:** Monitor for public threat intelligence disclosures of novel destructive malware (wiper) campaigns attributed to state-sponsored actors operating within Middle Eastern financial networks.

**Collection Method:** Monitor cybersecurity vendor threat intelligence blogs and CERT publications for wiper tooling disclosures with MENA attribution.

**Primary Sources:**
- Mandiant/Google TAG Blog (cloud.google.com/blog/topics/threat-intelligence) -- publishes Iran-attributed malware analysis; comprehensive technical disclosure
- ESET WeLiveSecurity (welivesecurity.com) -- publishes malware family analysis including MENA-theater wiper campaigns
- Check Point Research (research.checkpoint.com) -- frequently first-publisher on wiper malware targeting Israeli and GCC financial networks
- Kaspersky ICS CERT (ics-cert.kaspersky.com) -- publishes sanitized threat reports on OT and financial sector malware with regional attribution
- UK NCSC (ncsc.gov.uk/news) -- formal government attribution statements on state-sponsored cyber campaigns

---

## Indicator 1.3: Rhetorical Shifts and Diplomatic Withdrawals Signaling Breakdown of Back-Channel Communications

**Purpose:** Departure of mediators and red line declarations indicate that diplomatic safety valves are closing, increasing kinetic risk.

### SIR 1.3.1
**Requirement:** Report the departure or notable absence of senior diplomatic staff or special envoys from established neutral mediation hubs in Muscat (Oman) and Doha (Qatar).

**Collection Method:** Monitor official embassy and foreign ministry statements, Gulf-focused press, and US State Department readout releases for mediator movement language.

**Primary Sources:**
- Omani Ministry of Foreign Affairs (mofa.gov.om) -- Oman hosts the primary US-Iran back-channel; watch for senior visitor announcements and departures
- Qatar News Agency (qna.org.qa/en) -- Qatar hosts Hamas political bureau and serves as a US-facilitated diplomatic node; official wire for mediation activity
- US State Department Press Briefings (state.gov/press-briefings) -- official US diplomatic positioning; readouts of senior diplomatic contact in Gulf hubs
- Reuters Gulf Desk (reuters.com/world/middle-east) -- most reliable wire for breaking diplomatic developments in the Gulf region
- Al-Monitor (al-monitor.com) -- policy-focused; country-specific pulse trackers including Oman and Qatar mediation coverage

### SIR 1.3.2
**Requirement:** Identify state-level declarations of formal red lines by Iranian officials, IRGC commanders, or affiliated proxy leadership regarding maritime transit through the Strait of Hormuz or the Bab al-Mandab strait.

**Collection Method:** Monitor Iranian state media, IRGC official communications, and translated transcripts for declaratory language escalating maritime red line claims.

**Primary Sources:**
- IRNA (en.irna.ir and irna.ir) -- official Islamic Republic News Agency; both English and Farsi feeds; authoritative for official Iranian positioning
- Tasnim News (tasnimnews.com/en) -- IRGC-affiliated; reflects hardliner positioning and operational threat declarations
- MEMRI (memri.org) -- English translations of Farsi, Arabic, and Turkish state media statements; essential for non-Farsi readers monitoring red line language
- PressTV (presstv.ir) -- Iranian English-language broadcaster; official line on maritime posture claims
- IRGC Official Website (sepah.ir) -- official IRGC announcements in Farsi; watch for operational framing and commander statements

### SIR 1.3.3
**Requirement:** Monitor IAEA Director General statements and Board of Governors meeting outcomes for language indicating Iranian non-cooperation with safeguards inspectors, restriction of inspector access to declared or undeclared sites, or Iranian notification of further enrichment expansion. Any of these signals a diplomatic-to-operational shift on the nuclear track that materially increases conflict risk.

**Collection Method:** Monitor IAEA public reports and Board of Governors meeting outcomes; cross-reference with arms control analysis community for interpretation.

**Primary Sources:**
- IAEA Iran Safeguards (iaea.org/topics/iran) -- primary authoritative source; quarterly reports on enrichment levels and inspector access status
- James Martin Center for Nonproliferation Studies (nonproliferation.org/research/iran) -- satellite imagery analysis of Natanz, Fordow, and Isfahan nuclear sites
- Arms Control Association (armscontrol.org) -- JCPOA compliance tracker; rapid analysis of IAEA developments and diplomatic milestones
- ISIS -- Institute for Science and International Security (isis-online.org) -- most detailed open-source Iranian nuclear program analysis; David Albright publications
- Arms Control Wonk (armscontrolwonk.com) -- technical analysis; often first to publicly interpret IAEA report language in accessible terms

---

## Indicator 1.4: Anomalous Electronic Warfare (EW) and Position, Navigation, and Timing (PNT) Interference

**Purpose:** GPS jamming and spoofing in this theater are documented precursors and accompaniments to IRGC and IAMG kinetic operations, and indicate active EW preparation or ongoing operational activity.

### SIR 1.4.1
**Requirement:** Monitor commercial aviation GPS degradation logs for sudden clusters of position interference or denial events in the Levant airspace zone (Lebanon, Syria, and northern Israel) and the Strait of Hormuz and Persian Gulf approaches.

**Collection Method:** Real-time GPS jamming map monitoring; cross-reference with NOTAM database and aviation incident reports.

**Primary Sources:**
- GPSJam.org (gpsjam.org) -- live map of GPS interference aggregated from ADS-B reports; primary source; updated hourly; Levant and Gulf zones are persistently monitored
- OPSGROUP GPS Jamming Map (ops.group/blog/gpsjam) -- aviation community reports from pilot NOTAMs and ADS-B anomalies; Lebanon and Hormuz corridors persistently flagged
- EUROCONTROL GNSS Monitoring (eurocontrol.int/service/gnss-monitoring) -- official aviation GNSS interference reports; regional coverage
- ADS-B Exchange (globe.adsbexchange.com) -- filter by Navigation Accuracy Category (NACp) equal to low; identifies degraded GPS zones in real time
- FlightRadar24 (flightradar24.com) -- position jump artifacts on approach routes identify active GPS spoofing in Iran, Lebanon, and Hormuz corridors

### SIR 1.4.2
**Requirement:** Monitor Iranian military procurement announcements, defense technology press, and open-source imagery of IRGC parades and exercises for evidence of transition to jam-resistant satellite navigation systems (BeiDou-3 or GLONASS) integrated into IRGC drone platforms, fast attack craft, or missile transporter erector launchers (TELs).

**Collection Method:** Monitor Farsi-language defense press, English-language defense trade publications, and open-source satellite imagery and video from Iranian state-broadcast military events.

**Primary Sources:**
- Tasnim News (tasnimnews.com/en) -- IRGC-affiliated; publishes procurement announcements and IRGC capability claims; available in both Farsi and English
- Mehr News Agency (mehrnews.com/en) -- state-affiliated; covers defense technology procurement and military technology announcements
- CSIS Missile Defense Project (missilethreat.csis.org) -- documents IRGC missile system capabilities and navigation technology; free database
- C4ISRNET (c4isrnet.com/electronic-warfare) -- trade publication covering EW and navigation system developments relevant to the MENA theater
- Sentinel Hub EO Browser (apps.sentinel-hub.com/eo-browser) -- satellite imagery of Iranian military bases and parade staging areas for equipment observation and change detection

### SIR 1.4.3
**Requirement:** Detect widespread spoofing of Automatic Identification System (AIS) data for commercial vessels transiting the Persian Gulf and Strait of Hormuz, resulting in false geographic positions such as ships appearing inland, stationary, or in implausible formations.

**Collection Method:** AIS anomaly monitoring; cross-reference with satellite imagery (Sentinel-1 SAR) to detect positional spoofing against physically confirmed vessel locations.

**Primary Sources:**
- MarineTraffic Hormuz Feed (marinetraffic.com/en/ais/details/ports/1162) -- primary AIS monitoring; watch for inland or implausible vessel positions in the Strait area
- VesselFinder (vesselfinder.com) -- secondary AIS platform; cross-reference against MarineTraffic for spoofing confirmation through discrepancy analysis
- Windward AI (windward.ai/resources) -- publishes free behavioral analytics on Iran-linked AIS spoofing and sanctions-evasion vessel patterns
- SkyTruth / Global Fishing Watch (globalfishingwatch.org) -- flags AIS positional anomalies using satellite imagery cross-reference
- UKMTO (ukmto.org) -- issues spoofing and AIS anomaly advisories for Gulf of Oman and Hormuz within hours of reported incidents

---

## Indicator 1.5: Coordinated Narrative Warfare and Psychological Operations

**Purpose:** Information operations in this theater are a pre-kinetic and concurrent activity; detecting coordination enables early warning and reduces the risk of analytical deception.

### SIR 1.5.1
**Requirement:** Monitor national cybersecurity authority advisories and cybersecurity journalism for disclosed compromises of high-volume civilian mobile applications -- including religious calendar apps, local news aggregators, or regional messaging platforms -- used to push anti-regime or anti-coalition messaging to civilian populations in the Levant, Iraq, or the Gulf.

**Collection Method:** Monitor national CERT publications and security journalism for app-layer or mobile supply chain compromise disclosures; note that these events are observable only after disclosure, not in real time.

**Primary Sources:**
- Israeli National Cyber Directorate (INCD) -- gov.il/en/departments/national-cyber-directorate; issues public alerts on compromised civilian applications targeting Israeli users
- Saudi CERT (cert.gov.sa) -- publishes advisories on mobile application threats targeting the Saudi civilian population
- UAE Telecommunications and Digital Government Regulatory Authority (tdra.gov.ae) -- UAE CERT advisories on mobile threats in the Gulf
- Haaretz Tech Desk (haaretz.com) -- frequently covers Israeli cybersecurity incidents including app-layer and supply chain compromises
- Wired and ArsTechnica (wired.com / arstechnica.com) -- covers major mobile security disclosures with MENA regional implications

### SIR 1.5.2
**Requirement:** Identify the emergence of OSINT imposter accounts on X (Twitter) or Telegram that utilize AI-generated or misattributed satellite imagery to falsely claim successful strikes on high-priority targets.

**Collection Method:** Social media monitoring combined with satellite imagery cross-verification and geolocation analysis using Bellingcat-style methodology.

**Primary Sources:**
- X Advanced Search (twitter.com/search-advanced) -- Boolean and time-bounded search for accounts claiming strikes against known facility coordinates; filter by new account creation dates
- Sentinel Hub EO Browser (apps.sentinel-hub.com/eo-browser) -- directly verify claimed strike imagery against current facility status using Sentinel-2 optical and Sentinel-1 SAR before and after comparison
- Bellingcat Investigation Tools (bellingcat.com) -- SunCalc shadow analysis, Google Street View geolocation, and Jeffrey Exif Viewer (exif.regex.info) for metadata verification
- GeoConfirmed (X account @GeoConfirmed) -- active geolocation verification team; publishes rapid debunks during active disinformation events
- tgstat.com -- check subscriber-to-view ratio anomalies on new channels claiming strike footage; high views and low subscribers indicates likely coordinated artificial amplification

### SIR 1.5.3
**Requirement:** Monitor for coordinated inauthentic behavior patterns on X and Telegram, including accounts created within a 48-hour window sharing identical or near-identical crisis framing hashtags in Arabic, Hebrew, or Farsi -- particularly content invoking existential threat or mass casualty narratives -- with a threshold of 300 percent or greater spike in volume compared to the 72-hour baseline.

**Collection Method:** Social media monitoring using X Advanced Search and Telegram analytics; apply IO Detection Checklist protocols per OSINT source database.

**Primary Sources:**
- X Advanced Search (twitter.com/search-advanced) -- filter by account creation date and keyword; identify clusters of new accounts using identical hashtag strings across Arabic, Hebrew, and Farsi language spaces
- tgstat.com -- Telegram channel statistics; growth spike detection; new channel identification in a given region during an escalation window; identifies artificial amplification
- Telemetr.io (telemetr.io) -- message volume analytics across Telegram channels; cross-channel message duplication detection for coordinated content
- MEMRI (memri.org) -- tracks Arabic, Farsi, and Hebrew social media campaigns; publishes analysis of coordinated hashtag operations and narrative warfare events
- Bellingcat IO Archive (bellingcat.com/tag/information-operations) -- methodology reference for attribution and coordinated inauthentic behavior pattern analysis

### SIR 1.5.4
**Requirement:** Monitor Middle Eastern state television broadcasts in Iran, Iraq, Lebanon, and Yemen for synchronized crisis narratives appearing across multiple state-aligned media simultaneously, indicating coordinated strategic communication designed to prepare domestic and regional audiences for imminent escalation.

**Collection Method:** Monitor MEMRI TV Monitor project and regional pro-Iran media for coordinated broadcast content; flag when identical framing appears in Farsi, Arabic, and English outputs within the same 24-hour window.

**Primary Sources:**
- MEMRI TV Monitor (memri.org/tv) -- English-translated clips from Iranian (Press TV, IRIB), Hezbollah (Al Manar), and Houthi (Al Masirah) television; daily monitoring capability
- Al Manar English (english.almanar.com.lb) -- Hezbollah official media; monitor for mobilization or threat escalation framing changes
- Al Mayadeen (english.almayadeen.net) -- Resistance Axis regional network; reflects coordinated strategic messaging across the Iran-aligned media space
- Saba News Agency -- sabanews.net; Houthi-controlled state media; official Sanaa-aligned strategic messaging in Arabic
- Aparat.com (aparat.com) -- Iranian video hosting platform; contains regime-produced content often deleted from Telegram; monitor during escalation windows for mobilization video

---

## Indicator 1.6: Iranian Domestic Stability as an Escalation Driver

**Purpose:** Iranian external aggression historically correlates with domestic pressure cycles; regime insecurity at home drives externally-directed escalation as a distraction. This indicator tracks the domestic pressure variable.

### SIR 1.6.1
**Requirement:** Monitor Iran's unofficial US dollar parallel exchange rate for sustained depreciation trends, particularly rates exceeding 700,000 rials per USD, which historically correlate with domestic protest mobilization and regime pressure cycles that precede externally-directed escalation. Cross-reference with domestic unrest reporting.

**Collection Method:** Track Iran parallel FX rate on a daily basis; correlate with domestic protest and civil security reporting from independent Iran-focused media.

**Primary Sources:**
- BonBast.com (bonbast.com) -- Iran's unofficial USD/IRR exchange rate; most reliable open-source sanctions-pressure indicator; updated multiple times daily; rial depreciation spikes are a leading indicator
- Iran International (iranintl.com/en) -- London-based exile media; strongest open-source reporting on Iranian domestic unrest, protests, and IRGC internal security response
- IranWire (iranwire.com) -- investigative; diaspora and human rights focus; covers domestic economic conditions and protest reporting with sourcing from inside Iran
- Radio Farda (radiofarda.com) -- US-funded Farsi-language service (RFE/RL); widely monitored inside Iran; covers domestic economic conditions and civil unrest
- NetBlocks (netblocks.org) -- internet shutdown monitoring; Iranian internet throttling during domestic unrest events is detectable and correlated with crackdowns

### SIR 1.6.2
**Requirement:** Report IRGC or Basij public security operations in Tehran, Isfahan, or Mashhad -- observable through Farsi-language social media, diaspora news networks, and human rights monitoring platforms -- as indicators of regime domestic insecurity that historically precede external escalation operations intended to redirect domestic pressure.

**Collection Method:** Monitor Farsi-language social media, diaspora news networks, and human rights organizations for domestic Iranian security operation reporting.

**Primary Sources:**
- Iran Human Rights (IHRNGO) (iranhr.net) -- Oslo-based; documents IRGC and Basij security operations, arrests, and use of force against civilian demonstrators
- Aparat.com (aparat.com) -- Iranian video hosting; often contains footage of protest crackdowns before content is deleted from Telegram
- X Advanced Search (Farsi keywords) -- search by Farsi keywords for IRGC and Basij operational terms; breaking 6-12 hours before English-language reporting
- Iran International Telegram and X channels (iranintl.com) -- fastest English-language reporting on domestic Iranian security events
- IODA (Georgia Tech Internet Outage Detection) (ioda.inetintel.cc.gatech.edu) -- real-time internet outage mapping; regional internet blackouts in Iran during crackdowns are a corroborating signal

---

## Indicator 1.7: Humanitarian Conditions as an Instability Multiplier

**Purpose:** Humanitarian collapse in conflict-adjacent populations creates conditions for proxy recruitment, regime fragility, and displacement events that compound military instability. This indicator addresses the humanitarian domain required by the Big Question.

### SIR 1.7.1
**Requirement:** Monitor World Food Programme Situation Reports for Yemen, Syria, and Gaza for Integrated Food Security Phase Classification (IPC) Phase 4 (Emergency) or Phase 5 (Catastrophe) designations in governorates adjacent to active IAMG or Houthi operational zones, which indicate humanitarian collapse conditions that historically precede mass displacement, proxy recruitment surges, and regime fragility events.

**Collection Method:** Monthly monitoring of WFP situation reports and IPC classification updates; cross-reference with OCHA and ACAPS severity scoring.

**Primary Sources:**
- WFP Situation Reports (wfp.org/publications/situation-reports) -- monthly reports for Yemen, Syria, and Gaza; IPC classification by governorate; primary humanitarian indicator source
- OCHA MENA (unocha.org/middle-east-and-north-africa) -- UN humanitarian coordination; situation reports with access constraints and displacement data
- ACAPS (acaps.org) -- humanitarian crisis severity scoring; cross-regional comparison of conditions in IAMG-adjacent areas; free analytical products
- FAO Food Price Index (fao.org/worldfoodsituation/foodpricesindex/en) -- monthly; food price instability historically precedes MENA unrest by 3-6 months
- ReliefWeb (reliefweb.int) -- aggregates all MENA humanitarian situation reports; free; comprehensive coverage of all active crises

### SIR 1.7.2
**Requirement:** Monitor the IOM Displacement Tracking Matrix for sudden displacement events exceeding 50,000 persons within a 7-day window in Lebanon, Syria, or Iraq as leading indicators of kinetic escalation effects not yet captured by military reporting or official acknowledgment.

**Collection Method:** Weekly DTM dashboard monitoring; cross-reference with UNHCR operational portal and ACLED incident data to confirm displacement cause.

**Primary Sources:**
- IOM Displacement Tracking Matrix (dtm.iom.int) -- IOM population movement surveys; Iraq, Syria, Yemen; most current publicly available displacement data; sub-district level in active crises
- UNHCR Data Portal (data.unhcr.org) -- refugee and IDP figures by country; Lebanon, Jordan, and Iraq hosting population cross-reference
- IDMC (internal-displacement.org) -- Internal Displacement Monitoring Centre; IDP data by country and conflict cause; trend analysis capability
- ACLED (acleddata.com) -- cross-reference displacement spikes against geolocated SIGACT data to confirm cause-and-effect relationship between kinetic activity and population movement
- FRONTEX Risk Analysis (frontex.europa.eu/research/publications) -- EU border agency; Eastern Mediterranean and Aegean migration pressure data as secondary European spillover effect indicator

---

## Indicator 1.8: Iranian Nuclear Program Trajectory (Former PIR 4 Integration)

**Purpose:** The Iranian nuclear program is the central strategic driver of the US-Iran-Israel conflict threshold and must be tracked as a primary instability driver independent of the diplomatic channel. Enrichment levels and weaponization indicators operate on faster decision timelines than any other variable in the framework. A single credible Iranian breakout determination is the most likely trigger for an Israeli unilateral strike. This indicator elevates nuclear tracking from a sub-indicator of diplomacy to a primary instability signal requiring dedicated collection.

### SIR 1.8.1
**Requirement:** Monitor IAEA quarterly safeguards reports and Board of Governors meeting outcomes for Iranian enrichment levels at Fordow and Natanz -- specifically any increase toward 90 percent weapons-grade enrichment, centrifuge cascade expansion, or restriction of inspector access to declared sites -- as direct indicators of Iranian movement toward a nuclear threshold that materially increases Israeli and US preventive strike calculus.

**Collection Method:** Monitor IAEA publications quarterly; supplement with arms control analysis community interpretation within 24 hours of Board meetings; cross-reference ISIS and CNS satellite imagery for facility-specific corroboration.

**Primary Sources:**
- IAEA Iran Safeguards Reports (iaea.org/topics/iran) -- primary authoritative source; quarterly enrichment levels, centrifuge count, inspector access status; A-rating for declared facilities
- ISIS -- Institute for Science and International Security (isis-online.org) -- most detailed open-source Iranian nuclear program analysis; satellite imagery of Natanz, Fordow, Parchin, and Isfahan; David Albright publications
- James Martin Center for Nonproliferation Studies (nonproliferation.org/research/iran) -- Middlebury Institute; satellite imagery analysis of declared and suspected Iranian nuclear sites
- Arms Control Association JCPOA Tracker (armscontrol.org) -- compliance milestone tracking; rapid analysis of IAEA developments with diplomatic context; publishes within 24 hours of Board meetings
- Arms Control Wonk (armscontrolwonk.com) -- technical interpretation of IAEA enrichment language; enrichment-to-breakout timeline calculations in accessible format

### SIR 1.8.2
**Requirement:** Monitor satellite imagery of Iranian nuclear facility sites -- Fordow (underground enrichment), Natanz (main enrichment), Parchin (high-explosive testing), and Isfahan (uranium conversion) -- for new construction, excavation, equipment movement, or hardening activity that indicates program expansion, facility protection, or preparation to shift declared operations underground beyond IAEA inspector reach.

**Collection Method:** Monthly satellite imagery review of key Iranian nuclear sites using free platforms; cross-reference with ISIS and CNS analysis for change detection interpretation.

**Primary Sources:**
- Sentinel Hub EO Browser (apps.sentinel-hub.com/eo-browser) -- Sentinel-1 SAR and Sentinel-2 optical; free; 5-day revisit; detect construction, vehicle concentrations, and surface changes at Fordow, Natanz, Parchin, and Isfahan
- ISIS Nuclear Iran (isis-online.org) -- publishes annotated satellite imagery analysis of Iranian nuclear sites; facility-specific change detection with historical baseline comparison
- James Martin CNS (nonproliferation.org) -- periodic satellite analysis of Iranian nuclear sites with facility diagrams and annotated observable changes
- Planet Labs Explorer Free Tier (planet.com/explorer) -- 3-5m resolution optical; limited free access; highest spatial resolution among free platforms for visible surface changes at known facility coordinates
- Google Earth Pro (earth.google.com) -- historical imagery slider; construction baseline comparison at known Iranian nuclear site coordinates

### SIR 1.8.3
**Requirement:** Monitor nonproliferation research publications and the DNI Annual Threat Assessment for disclosed indicators of Iranian weaponization-track activity -- including high-explosive lens testing at Parchin, neutron initiator research, re-entry vehicle development, or nuclear weapon design work -- which are analytically distinct from enrichment and indicate movement toward an assembled weapon rather than fissile material production alone.

**Collection Method:** Monitor nonproliferation specialist publications and US intelligence community unclassified annual assessments; weaponization indicators have longer disclosure lag than enrichment data and require specialist interpretation.

**Primary Sources:**
- DNI Annual Threat Assessment (dni.gov/index.php/newsroom/reports-publications) -- released February annually; unclassified IC assessment of Iranian nuclear weaponization status; A-rating for official US government position
- ISIS (isis-online.org) -- publishes analysis of suspected weaponization indicators including Parchin high-explosive testing and neutron initiator research; primary open-source weaponization reference
- IAEA Board of Governors GOV documents (iaea.org) -- when IAEA raises possible military dimensions (PMD) concerns, the GOV document language is the most authoritative open-source weaponization indicator
- Federation of American Scientists Nuclear Notebook (fas.org/niw) -- Iran nuclear capability assessments updated periodically by former government analysts; free
- Stimson Center Nonproliferation (stimson.org/programs/middle-east-south-asia) -- Iran nuclear analysis with weaponization-track framing analytically distinct from enrichment reporting

---

## Indicator 1.9: Buffer State Political Cohesion and Institutional Fragility (Former PIR 6 Integration)

**Purpose:** Lebanon, Iraq, and Jordan function as the containment perimeter for regional conflict. Their institutional fragility determines whether IAMG operations are practically constrained by host state governance or effectively unconstrained. Buffer state fragility is a structural enabling condition for escalation, not merely a consequence of it. These states also represent the primary vectors for conflict-driven European migration pressure, making their stability directly relevant to NATO political cohesion.

### SIR 1.9.1
**Requirement:** Monitor Lebanese economic collapse indicators -- including the Lebanese pound parallel exchange rate, banking sector capital access restrictions, and power grid service hours per day -- alongside Hezbollah political constraint capacity indicators, as measures of the degree to which the Lebanese state retains any practical ability to constrain Hezbollah operational decisions independent of Tehran direction.

**Collection Method:** Monitor Lebanese economic data through regional financial press and OSINT economic tracking; cross-reference with ICG Lebanon analysis and Carnegie Middle East Center for institutional capacity assessment.

**Primary Sources:**
- L'Orient Today (today.lorientlejour.com) -- Beirut-based independent English-language; strongest open-source reporting on Lebanese economic conditions, political paralysis, and Hezbollah-state relations
- ICG Crisis Watch Lebanon (crisisgroup.org/crisis-watch) -- monthly escalation and improvement status; Lebanon institutional fragility tracking with field-based sourcing
- Carnegie Middle East Center Beirut (carnegie-mec.org) -- field-embedded analysis; best open-source assessment of Hezbollah-Lebanese state dynamics and Iranian direction of Hezbollah operations
- Xe.com LBP (xe.com) -- Lebanese pound exchange rate monitoring; sustained depreciation beyond 100,000 LBP per USD reflects near-total state economic incapacity and proxies for institutional constraint collapse
- World Bank Lebanon Economic Monitor (worldbank.org/en/country/lebanon) -- quarterly; documents Lebanese financial collapse and state service delivery failure; structural context for constraint capacity assessment

### SIR 1.9.2
**Requirement:** Monitor Iraqi government coalition stability -- specifically PMF-government relationship indicators, Kurdish Regional Government (KRG) political alignment with Baghdad, and parliamentary debate on IAMG operational presence in Iraqi territory -- as indicators of whether the Iraqi state can or will constrain IAMG escalatory behavior originating from Iraqi soil.

**Collection Method:** Monitor Iraqi political press and ICG Iraq analysis; supplement with OIR reporting and KRG-focused media for sub-national political fragmentation assessment.

**Primary Sources:**
- Al-Mada (almadapaper.net -- Arabic) -- one of few non-partisan Iraqi newspapers; covers PMF-Baghdad political relations with genuine editorial independence; essential for Iraqi political fragmentation monitoring
- Rudaw (rudaw.net/english) -- Kurdish regional news; strongest open-source reporting on KRG-Baghdad relations and Kurdish positions on IAMG presence in northern Iraq
- Shafaq News (shafaq.com/en) -- Erbil-based; covers PMF activity, KRG security incidents, and Baghdad political dynamics with good sub-provincial granularity
- ICG Iraq (crisisgroup.org/middle-east-north-africa/gulf-and-arabian-peninsula/iraq) -- Iraq political assessments; PMF-state relations and government formation analysis with field sourcing
- OIR Operation Inherent Resolve (inherentresolve.mil) -- acknowledges IAMG-government tension incidents from the US operational perspective; cross-reference with Iraqi press for the full political picture

### SIR 1.9.3
**Requirement:** Monitor Jordanian domestic political stability indicators -- including Palestinian population sentiment expressed through Jordanian social media, tribal leader public statements, economic pressure markers, and Jordanian government public positioning on regional escalation -- given Jordan's role as a critical US partner, airspace transit state, and the US ally most vulnerable to displacement-driven domestic destabilization from a Gaza or West Bank escalation cascade.

**Collection Method:** Monitor Jordanian news and economic indicators; supplement with ICG Jordan analysis and US Embassy security messaging for institutional stress signals.

**Primary Sources:**
- Jordan Times (jordantimes.com) -- independent English-language Amman press; covers Jordanian domestic politics, economic conditions, and government positioning on regional events
- Petra News Agency (petra.gov.jo/en) -- official Jordanian state wire; government position statements; detect shifts in Jordanian alignment language toward or away from US partner posture
- ICG Jordan Analysis (crisisgroup.org) -- Jordanian domestic political assessments; Palestinian refugee population dynamics and tribal political economy analysis with field-sourced context
- Trading Economics Jordan (tradingeconomics.com) -- Jordanian dinar, inflation, and unemployment data; economic pressure on a buffer state is a structural fragility variable with direct alliance implications
- US Embassy Amman Security Messages (jo.usembassy.gov/messages-for-us-citizens) -- underutilized early warning source; security alerts often precede formal advisory changes by 24-48 hours
