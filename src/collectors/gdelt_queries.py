"""
SENTINEL2 — SIR-to-GDELT Query Template Registry
Maps each Specific Information Requirement (SIR) to one or more
GDELT DOC 2.0 API queries with theme/keyword combinations.
"""

# Each entry: (query_text, gdelt_theme_filter, source_country_filter)
# theme and sourcecountry are optional (None = no filter)

SIR_QUERY_MAP: dict[str, list[dict]] = {
    # ================================================================
    # PIR 1: Instability Drivers — Greater Middle East
    # ================================================================

    # 1.1: IAMG Mobilization/Repositioning
    "SIR1.1.1": [
        {"query": "militia weapons missile repositioning Iraq Syria", "theme": "MILITARY"},
        {"query": "Hezbollah military deployment Lebanon", "theme": "MILITARY"},
        {"query": "Kata'ib Hezbollah rocket launch position", "theme": None},
    ],
    "SIR1.1.2": [
        {"query": "militia Telegram channel blackout silence", "theme": None},
        {"query": "Hezbollah media statement military", "theme": None},
    ],
    "SIR1.1.3": [
        {"query": "civilian evacuation militia compound Iraq Syria Lebanon", "theme": None},
    ],

    # 1.2: State-Sponsored Cyber Activity
    "SIR1.2.1": [
        {"query": "cyber attack energy infrastructure Israel Gulf", "theme": "CYBER_ATTACK"},
        {"query": "SCADA ICS attack water desalination Middle East", "theme": None},
    ],
    "SIR1.2.2": [
        {"query": "malware destructive wiper Iran cyber campaign", "theme": "CYBER_ATTACK"},
        {"query": "APT state-sponsored hack Middle East", "theme": None},
    ],

    # 1.3: Rhetorical Shifts and Diplomatic Withdrawals
    "SIR1.3.1": [
        {"query": "diplomat withdrawal recall mediation Oman Qatar", "theme": "DIPLOMACY"},
        {"query": "embassy closure recall ambassador Middle East", "theme": None},
    ],
    "SIR1.3.2": [
        {"query": "red line Strait of Hormuz Bab al-Mandeb threat", "theme": None},
        {"query": "Iran threat close shipping lane", "theme": None},
    ],
    "SIR1.3.3": [
        {"query": "IAEA safeguards non-cooperation Iran inspector", "theme": "WMD"},
    ],

    # 1.4: EW and PNT Interference
    "SIR1.4.1": [
        {"query": "GPS jamming spoofing Eastern Mediterranean Levant", "theme": None},
        {"query": "GPS interference aviation Middle East", "theme": None},
    ],
    "SIR1.4.2": [
        {"query": "Iran BeiDou GLONASS navigation procurement", "theme": None},
    ],
    "SIR1.4.3": [
        {"query": "AIS spoofing Persian Gulf Strait of Hormuz vessel", "theme": "MARITIME_INCIDENT"},
    ],

    # 1.5: Coordinated Narrative Warfare
    "SIR1.5.1": [
        {"query": "mobile app hack compromise propaganda Middle East", "theme": None},
    ],
    "SIR1.5.2": [
        {"query": "fake OSINT false flag strike claim social media", "theme": None},
    ],
    "SIR1.5.3": [
        {"query": "bot network coordinated inauthentic behavior Middle East", "theme": None},
        {"query": "troll farm disinformation campaign Iran Russia", "theme": None},
    ],
    "SIR1.5.4": [
        {"query": "state media synchronized narrative Iran Russia propaganda", "theme": None},
    ],

    # 1.6: Iranian Domestic Stability
    "SIR1.6.1": [
        {"query": "Iran rial exchange rate black market currency", "theme": "ECON_BANKRUPTCY"},
    ],
    "SIR1.6.2": [
        {"query": "IRGC Basij crackdown protest Tehran Isfahan Mashhad", "theme": "PROTEST"},
        {"query": "Iran security forces arrest opposition", "theme": None},
    ],

    # 1.7: Humanitarian Conditions
    "SIR1.7.1": [
        {"query": "famine IPC phase food crisis Yemen Syria Gaza", "theme": "FOOD_SECURITY"},
        {"query": "humanitarian crisis starvation blockade", "theme": "REFUGEES"},
    ],
    "SIR1.7.2": [
        {"query": "mass displacement refugee surge Syria Yemen Iraq", "theme": "REFUGEES"},
        {"query": "UNHCR displacement population movement", "theme": None},
    ],

    # 1.8: Iranian Nuclear Program
    "SIR1.8.1": [
        {"query": "Iran enrichment uranium 60 90 percent IAEA", "theme": "WMD"},
        {"query": "Iran nuclear weapons grade enrichment centrifuge", "theme": None},
    ],
    "SIR1.8.2": [
        {"query": "Iran nuclear facility satellite imagery construction Natanz Fordow", "theme": "WMD"},
    ],
    "SIR1.8.3": [
        {"query": "Iran Parchin nuclear test weaponization neutron", "theme": "WMD"},
    ],

    # 1.9: Buffer State Cohesion
    "SIR1.9.1": [
        {"query": "Lebanon economic collapse Hezbollah political crisis", "theme": None},
    ],
    "SIR1.9.2": [
        {"query": "Iraq government coalition PMF militia political", "theme": None},
    ],
    "SIR1.9.3": [
        {"query": "Jordan stability protest Palestinian sentiment", "theme": None},
    ],

    # ================================================================
    # PIR 2: Global Security Impact and Force Deployment Triggers
    # ================================================================

    # 2.1: Energy Supply Chain Disruption
    "SIR2.1.1": [
        {"query": "Iran fast attack craft mine-laying vessel Hormuz shipping lane", "theme": "MARITIME_INCIDENT"},
        {"query": "Iran navy boat tanker harassment Persian Gulf", "theme": None},
    ],
    "SIR2.1.2": [
        {"query": "Brent crude oil price spike volatility Middle East", "theme": "ECON_OIL"},
    ],
    "SIR2.1.3": [
        {"query": "war risk insurance premium Red Sea Persian Gulf Mediterranean", "theme": None},
        {"query": "shipping insurance cost increase conflict zone", "theme": None},
    ],

    # 2.2: Mutual Defense Agreement Activation
    "SIR2.2.1": [
        {"query": "THAAD Patriot air defense deployment Israel Gulf", "theme": "MILITARY"},
    ],
    "SIR2.2.2": [
        {"query": "NATO Response Force VJTF activation readiness", "theme": "ALLIANCE"},
    ],
    "SIR2.2.3": [
        {"query": "Congress emergency authorization military Middle East", "theme": None},
    ],

    # 2.3: Geographic Expansion
    "SIR2.3.1": [
        {"query": "attack strike Western assets Red Sea Gulf of Aden", "theme": "ARMEDCONFLICT"},
        {"query": "Houthi attack commercial vessel Red Sea", "theme": None},
    ],
    "SIR2.3.2": [
        {"query": "Russian Chinese naval presence surveillance Mediterranean Gulf", "theme": None},
    ],
    "SIR2.3.3": [
        {"query": "Houthi expanded range new weapon capability missile drone", "theme": None},
    ],

    # 2.4: Strategic Resource Weaponization
    "SIR2.4.1": [
        {"query": "Iran food commodity stockpile export ban restriction", "theme": None},
    ],
    "SIR2.4.2": [
        {"query": "semiconductor neon helium supply disruption Middle East", "theme": None},
    ],
    "SIR2.4.3": [
        {"query": "Caspian Sea container traffic Middle Corridor trade route", "theme": None},
    ],

    # 2.5: Tactical Dark Activity
    "SIR2.5.1": [
        {"query": "dark ship AIS off vessel loitering Hormuz Bab al-Mandeb", "theme": "MARITIME_INCIDENT"},
    ],
    "SIR2.5.2": [
        {"query": "US military airlift surge transport aircraft Middle East", "theme": "MILITARY"},
    ],
    "SIR2.5.3": [
        {"query": "evacuation Western corporate personnel Gulf departure", "theme": None},
    ],

    # 2.6: European Economic Spillover
    "SIR2.6.1": [
        {"query": "European LNG natural gas price spike energy crisis", "theme": "ECON_OIL"},
    ],
    "SIR2.6.2": [
        {"query": "food price index grain wheat futures chokepoint disruption", "theme": "FOOD_SECURITY"},
    ],

    # 2.7: NATO Cohesion and Turkish Positioning
    "SIR2.7.1": [
        {"query": "Turkey Incirlik airspace Bosphorus access NATO", "theme": None},
    ],
    "SIR2.7.2": [
        {"query": "Turkey Iran economic diplomatic energy cooperation", "theme": None},
    ],

    # ================================================================
    # PIR 3: Stabilizing Forces and De-escalation
    # ================================================================

    # 3.1: Active Diplomatic Mediation
    "SIR3.1.1": [
        {"query": "Oman Qatar mediation Iran United States prisoner exchange", "theme": "DIPLOMACY"},
        {"query": "diplomatic channel backchannel Iran negotiations", "theme": None},
    ],
    "SIR3.1.2": [
        {"query": "IAEA inspector access Iran enrichment reduction", "theme": "WMD"},
    ],

    # 3.2: Reduction in IAMG Operational Tempo
    "SIR3.2.1": [
        {"query": "militia ceasefire reduction attack frequency Iraq Syria", "theme": "CEASEFIRE"},
    ],
    "SIR3.2.2": [
        {"query": "militia leader statement pause restraint strategic patience", "theme": None},
    ],

    # 3.3: Economic Normalization Signals
    "SIR3.3.1": [
        {"query": "Iran rial appreciation stock market TEDPIX recovery", "theme": None},
    ],
    "SIR3.3.2": [
        {"query": "Saudi Iran normalization trade delegation joint commission", "theme": "DIPLOMACY"},
    ],

    # 3.4: International Stabilization Measures
    "SIR3.4.1": [
        {"query": "UN Security Council ceasefire humanitarian corridor", "theme": "CEASEFIRE"},
    ],
    "SIR3.4.2": [
        {"query": "IMF World Bank emergency lending conflict state", "theme": None},
    ],

    # ================================================================
    # PIR 4: Great Power Competition
    # ================================================================

    # 4.1: Russian Diplomatic Cover and Military Tech Transfer
    "SIR4.1.1": [
        {"query": "Russia veto UN Security Council Iran resolution", "theme": None},
    ],
    "SIR4.1.2": [
        {"query": "Russia Iran military technology transfer drone air defense missile", "theme": "ARMS_SALE"},
        {"query": "Shahed drone Russia Iran military cooperation", "theme": None},
    ],
    "SIR4.1.3": [
        {"query": "Russia Iran coordinated messaging propaganda information operation", "theme": None},
    ],

    # 4.2: Chinese Economic Enabling
    "SIR4.2.1": [
        {"query": "Iran crude oil export China ghost tanker sanctions", "theme": "ECON_SANCTIONS"},
    ],
    "SIR4.2.2": [
        {"query": "China dual-use technology transfer Iran UAE Malaysia", "theme": "TECHNOLOGY_TRANSFER"},
    ],
    "SIR4.2.3": [
        {"query": "China IAEA blocking nuclear compliance Iran", "theme": None},
    ],

    # 4.3: Russia-China Strategic Coordination
    "SIR4.3.1": [
        {"query": "SCO summit Russia China Iran trilateral cooperation", "theme": None},
    ],
    "SIR4.3.2": [
        {"query": "China Russia navy joint exercise Gulf of Oman Arabian Sea", "theme": "MILITARY_EXERCISE"},
    ],
}


def get_queries_for_pir(pir_id: str) -> list[dict]:
    """Return all GDELT queries associated with a given PIR."""
    prefix = pir_id.replace("PIR", "SIR")  # PIR1 → SIR1
    results = []
    for sir_id, queries in SIR_QUERY_MAP.items():
        if sir_id.startswith(prefix):
            for q in queries:
                results.append({
                    "sir_id": sir_id,
                    "query": q["query"],
                    "theme": q.get("theme"),
                    "sourcecountry": q.get("sourcecountry"),
                })
    return results


def get_all_queries() -> list[dict]:
    """Return all SIR queries as a flat list."""
    results = []
    for sir_id, queries in SIR_QUERY_MAP.items():
        pir_id = "PIR" + sir_id[3]  # SIR1.1.1 → PIR1
        for q in queries:
            results.append({
                "sir_id": sir_id,
                "pir_id": pir_id,
                "query": q["query"],
                "theme": q.get("theme"),
                "sourcecountry": q.get("sourcecountry"),
            })
    return results
