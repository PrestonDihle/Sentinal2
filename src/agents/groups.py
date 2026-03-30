"""
SENTINEL2 — Analysis Group Assignments
Targeted group composition per Section 3.4 of the project specification.
6 analysis groups (5 agents each) + reserve pool (19 agents).
Groups 1-4 map to PIRs 1-4, Group 5 = Black Swan, Group 6 = Big Question.
"""

import logging
from typing import Optional

from src.agents.definitions import get_agent, get_agent_keys, AGENT_REGISTRY

logger = logging.getLogger("sentinel2.agents.groups")

# ── Targeted Group Assignments ────────────────────────────────────────
# Each group: (group_id, pir_mapping, agent_keys)

GROUP_ASSIGNMENTS: dict[int, dict] = {
    1: {
        "name": "Group 1 — Threat & Security",
        "pir": 1,
        "description": "Security threats, terrorism, cyber, force protection",
        "agents": [
            "counter_terrorism_specialist",
            "israeli_intel_officer",
            "cyber_warfare_expert",
            "ems_operations_engineer",
            "dia_senior_analyst",
        ],
    },
    2: {
        "name": "Group 2 — Military & Maritime",
        "pir": 2,
        "description": "Force posture, naval ops, air power, logistics",
        "agents": [
            "nato_general_officer",
            "navy_admiral",
            "air_power_strategist",
            "maritime_expert",
            "supply_chain_expert",
        ],
    },
    3: {
        "name": "Group 3 — Diplomacy & Humanitarian",
        "pir": 3,
        "description": "Diplomatic developments, humanitarian crises, mediation",
        "agents": [
            "career_diplomat",
            "mediation_expert",
            "humanitarian_aid_expert",
            "usaid_officer",
            "islamic_jurisprudence_scholar",
        ],
    },
    4: {
        "name": "Group 4 — Great Power & Economy",
        "pir": 4,
        "description": "Great power competition, economic shifts, trade",
        "agents": [
            "russian_strategy_expert",
            "chinese_strategy_expert",
            "macro_economist_trade",
            "indo_pacific_analyst",
            "geopolitics_expert",
        ],
    },
    5: {
        "name": "Group 5 — Black Swan Detection",
        "pir": None,
        "description": "Low-probability high-impact event detection",
        "agents": [
            "behavioral_psychologist",
            "statistician_advanced",
            "data_science_expert",
            "environmental_security_specialist",
            "energy_grid_architect",
        ],
    },
    6: {
        "name": "Group 6 — Big Question",
        "pir": None,
        "description": "Meta-synthesis across all PIRs, strategic assessment",
        "agents": [
            "cia_senior_analyst",
            "american_general_officer",
            "geopolitical_strategy_expert",
            "finint_expert",
            "sociologist",
        ],
    },
}

# ── Reserve Pool ──────────────────────────────────────────────────────
# All agents not assigned to a group form the reserve pool.
# CMA can recommend rotations from reserve into active groups.

_ASSIGNED_AGENTS: set[str] = set()
for _grp in GROUP_ASSIGNMENTS.values():
    _ASSIGNED_AGENTS.update(_grp["agents"])

RESERVE_POOL: list[str] = [
    key for key in AGENT_REGISTRY.keys() if key not in _ASSIGNED_AGENTS
]


def get_group(group_id: int) -> dict:
    """Return group definition by ID (1-6)."""
    if group_id not in GROUP_ASSIGNMENTS:
        raise ValueError(f"Invalid group_id: {group_id}. Must be 1-6.")
    return GROUP_ASSIGNMENTS[group_id]


def get_group_agents(group_id: int) -> list:
    """Create and return CrewAI Agent instances for a group."""
    grp = get_group(group_id)
    return [get_agent(key) for key in grp["agents"]]


def get_group_for_pir(pir_number: int) -> Optional[dict]:
    """Return the group assigned to a specific PIR (1-4)."""
    for grp in GROUP_ASSIGNMENTS.values():
        if grp["pir"] == pir_number:
            return grp
    return None


def get_reserve_agents() -> list:
    """Create and return CrewAI Agent instances from the reserve pool."""
    return [get_agent(key) for key in RESERVE_POOL]


def get_reserve_keys() -> list[str]:
    """Return registry keys for reserve pool agents."""
    return list(RESERVE_POOL)


def rotate_agent(group_id: int, remove_key: str, add_key: str) -> bool:
    """
    Rotate an agent: move one out of a group into reserve,
    bring one from reserve into the group.

    Returns True if rotation succeeded.
    """
    grp = get_group(group_id)
    agents = grp["agents"]

    if remove_key not in agents:
        logger.warning(f"Agent '{remove_key}' not in group {group_id}")
        return False
    if add_key not in RESERVE_POOL:
        logger.warning(f"Agent '{add_key}' not in reserve pool")
        return False

    # Perform rotation
    idx = agents.index(remove_key)
    agents[idx] = add_key
    RESERVE_POOL.remove(add_key)
    RESERVE_POOL.append(remove_key)
    _ASSIGNED_AGENTS.discard(remove_key)
    _ASSIGNED_AGENTS.add(add_key)

    logger.info(f"Group {group_id}: rotated out '{remove_key}', rotated in '{add_key}'")
    return True


def get_group_summary() -> dict:
    """Return a summary of all group assignments for logging/reporting."""
    summary = {}
    for gid, grp in GROUP_ASSIGNMENTS.items():
        summary[gid] = {
            "name": grp["name"],
            "pir": grp["pir"],
            "agents": [AGENT_REGISTRY[k]["role"] for k in grp["agents"]],
        }
    summary["reserve"] = {
        "count": len(RESERVE_POOL),
        "agents": [AGENT_REGISTRY[k]["role"] for k in RESERVE_POOL],
    }
    return summary
