"""SENTINEL2 — Named Areas of Interest, Topics, and Reference Data (READ-ONLY)

Updated from Sentinel v1 with expanded coverage per the Sentinel2 prompt.
"""

# ── Countries (20 monitored) ─────────────────────────────────────────
COUNTRIES = [
    "Lebanon",
    "Syria",
    "Iraq",
    "Iran",
    "Israel",
    "Palestine",
    "Yemen",
    "Saudi Arabia",
    "UAE",
    "Qatar",
    "Bahrain",
    "Kuwait",
    "Oman",
    "Jordan",
    "Turkey",
    "Armenia",
    "Azerbaijan",
    "Georgia",
    "Egypt",
    "Libya",
]

# ── Terrorist / Militia Groups (15) ─────────────────────────────────
TERRORIST_GROUPS = [
    "Hezbollah",
    "Houthis (Ansar Allah)",
    "Hamas",
    "Palestinian Islamic Jihad",
    "ISIS/ISIL",
    "Al-Qaeda (AQ)",
    "AQAP",
    "Al-Shabaab",
    "PKK",
    "Kata'ib Hezbollah",
    "Asa'ib Ahl al-Haq",
    "Harakat al-Nujaba",
    "Popular Mobilization Forces (PMF/Hashd)",
    "Hayat Tahrir al-Sham (HTS)",
    "Islamic Resistance in Iraq",
]

# ── Transnational Organizations ─────────────────────────────────────
TRANSNATIONAL_ORGANIZATIONS = [
    "Kurdish peoples",
    "Shia Marjaʿiyya",
    "Tuareg/Berber communities",
    "Assyrians/Chaldeans",
    "Druze communities",
]

# ── Maritime Choke Points ───────────────────────────────────────────
MARITIME_CHOKE_POINTS = [
    "Strait of Hormuz",
    "Suez Canal",
    "Bab el-Mandeb",
    "Turkish Straits (Bosporus/Dardanelles)",
    "Straits of Tiran",
]

# ── Economic NAIs ───────────────────────────────────────────────────
ECONOMY_NAIS = [
    "Oil supply/pricing",
    "Commodities markets",
    "Bond markets/sovereign debt",
    "Food prices/security",
    "Precious metals",
]

# ── Topics (7 focus areas) ──────────────────────────────────────────
TOPICS = [
    "Air defense systems deployment",
    "Rotary-wing deployment patterns",
    "Nuclear proliferation indicators",
    "Chemical/biological weapons activity",
    "UAS/drone tactics and deployment",
    "Cyber operations and infrastructure",
    "Gray-zone/hybrid warfare adaptation",
]

# ── Categories of Military Intervention ─────────────────────────────
CATEGORIES_OF_MILITARY_INTERVENTION = {
    "Sovereignty and National Defense": (
        "This category encompasses the defense of a nation's physical borders "
        "and digital infrastructure. It utilizes kinetic military capabilities "
        "to repel direct attacks, cyber operations to shield critical national "
        "systems, and visible deployments to deter potential aggressors. The "
        "primary objective is the maintenance of internal security and the "
        "preservation of sovereign control."
    ),
    "Treaty and Alliance Obligations": (
        "These operations involve fulfilling international defense agreements "
        "and supporting multinational mandates to maintain regional order. "
        "This includes the enforcement of sanctions, such as no-fly zones, "
        "and the execution of stability operations to rebuild governance. "
        "These actions are designed to prevent state collapse and ensure "
        "compliance with global security frameworks."
    ),
    "Protection of Global Commons": (
        "This pillar focuses on securing international transit routes and "
        "preventing the proliferation of weapons of mass destruction. It "
        "includes maritime interventions to ensure the free flow of commerce, "
        "counter-piracy missions, and the protection of vital strategic "
        "resources. These activities maintain the integrity of the global "
        "trade network and resource access."
    ),
    "Interdiction and Civil Support": (
        "This category addresses non-state threats and domestic emergencies "
        "through interagency collaboration. It involves disrupting terrorist "
        "networks, supporting law enforcement against transnational crime, "
        "and providing heavy logistics for disaster relief. These missions "
        "are activated when civilian agencies are overwhelmed by natural "
        "disasters, public health crises, or significant civil unrest."
    ),
}

CATEGORIES_FULL_TEXT = """Categories of Military Intervention

1. Sovereignty and National Defense: This category encompasses the defense of a nation's physical borders and digital infrastructure. It utilizes kinetic military capabilities to repel direct attacks, cyber operations to shield critical national systems, and visible deployments to deter potential aggressors. The primary objective is the maintenance of internal security and the preservation of sovereign control.

2. Treaty and Alliance Obligations: These operations involve fulfilling international defense agreements and supporting multinational mandates to maintain regional order. This includes the enforcement of sanctions, such as no-fly zones, and the execution of stability operations to rebuild governance. These actions are designed to prevent state collapse and ensure compliance with global security frameworks.

3. Protection of Global Commons: This pillar focuses on securing international transit routes and preventing the proliferation of weapons of mass destruction. It includes maritime interventions to ensure the free flow of commerce, counter-piracy missions, and the protection of vital strategic resources. These activities maintain the integrity of the global trade network and resource access.

4. Interdiction and Civil Support: This category addresses non-state threats and domestic emergencies through interagency collaboration. It involves disrupting terrorist networks, supporting law enforcement against transnational crime, and providing heavy logistics for disaster relief. These missions are activated when civilian agencies are overwhelmed by natural disasters, public health crises, or significant civil unrest."""


# ── Convenience lookups ─────────────────────────────────────────────
ALL_NAATOIS = {
    "countries": COUNTRIES,
    "terrorist_groups": TERRORIST_GROUPS,
    "transnational_organizations": TRANSNATIONAL_ORGANIZATIONS,
    "maritime_choke_points": MARITIME_CHOKE_POINTS,
    "economy_nais": ECONOMY_NAIS,
    "topics": TOPICS,
}

# Country code mapping for GDELT queries
COUNTRY_CODES = {
    "Lebanon": "LB",
    "Syria": "SY",
    "Iraq": "IZ",
    "Iran": "IR",
    "Israel": "IS",
    "Palestine": "PS",
    "Yemen": "YM",
    "Saudi Arabia": "SA",
    "UAE": "AE",
    "Qatar": "QA",
    "Bahrain": "BH",
    "Kuwait": "KU",
    "Oman": "MU",
    "Jordan": "JO",
    "Turkey": "TU",
    "Armenia": "AM",
    "Azerbaijan": "AJ",
    "Georgia": "GG",
    "Egypt": "EG",
    "Libya": "LY",
}
