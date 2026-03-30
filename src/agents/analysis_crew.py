"""
SENTINEL2 — Analysis Crew Engine
Creates and runs CrewAI Crews for Groups 1-6 with Tree of Thought methodology.

Layer 3 of the pipeline:
  - Groups 1-4: PIR-mapped analysis (Claude Sonnet)
  - Group 5: Black Swan detection (Claude Sonnet)
  - Group 6: Big Question meta-synthesis (Claude Opus)
  - Group 6 runs after Groups 1-5 complete and reads their outputs.
"""

import json
import logging
from datetime import date
from typing import Optional
from pathlib import Path

from crewai import Agent, Crew, Task, Process, LLM

from src.agents.definitions import AGENT_REGISTRY, get_agent
from src.agents.groups import get_group, get_group_agents, GROUP_ASSIGNMENTS
from src.agents.context_loader import (
    build_analyst_context, format_context_block,
    load_pir_text, load_task_prompt,
)
from src.db.connection import execute_query, get_cursor
from src.utils.config import get_prompts_dir
from nais.reference import CATEGORIES_OF_MILITARY_INTERVENTION

logger = logging.getLogger("sentinel2.analysis_crew")


def run_analysis_groups(run_date: Optional[str] = None) -> dict:
    """
    Execute all 6 analysis groups sequentially.
    Groups 1-5 run first, then Group 6 reads their outputs.

    Returns dict with all group outputs and status.
    """
    if run_date is None:
        run_date = date.today().isoformat()

    logger.info(f"Starting analysis groups for {run_date}")

    # Build shared analyst context
    context = build_analyst_context(run_date)

    results = {}

    # Run Groups 1-5
    for group_id in range(1, 6):
        logger.info(f"Running Group {group_id}: {GROUP_ASSIGNMENTS[group_id]['name']}")
        try:
            output = _run_group(group_id, context, run_date)
            results[group_id] = output
            _store_assessment(group_id, run_date, output)
        except Exception as e:
            logger.error(f"Group {group_id} failed: {e}")
            results[group_id] = {"status": "failed", "error": str(e)}

    # Run Group 6 — Big Question (reads Groups 1-5 outputs)
    logger.info(f"Running Group 6: {GROUP_ASSIGNMENTS[6]['name']}")
    try:
        output = _run_group_6(context, results, run_date)
        results[6] = output
        _store_assessment(6, run_date, output)
    except Exception as e:
        logger.error(f"Group 6 failed: {e}")
        results[6] = {"status": "failed", "error": str(e)}

    logger.info(f"All analysis groups complete for {run_date}")
    return results


def run_single_group(
    group_id: int,
    run_date: Optional[str] = None,
    prior_outputs: Optional[dict] = None,
) -> dict:
    """Run a single analysis group (for testing or re-runs)."""
    if run_date is None:
        run_date = date.today().isoformat()

    context = build_analyst_context(run_date)

    if group_id == 6:
        if prior_outputs is None:
            prior_outputs = _load_prior_group_outputs(run_date)
        return _run_group_6(context, prior_outputs, run_date)

    return _run_group(group_id, context, run_date)


# ── Group Execution ───────────────────────────────────────────────────

def _run_group(group_id: int, context: dict, run_date: str) -> dict:
    """Run a single analysis group (1-5) as a CrewAI Crew."""
    grp = get_group(group_id)
    agents = get_group_agents(group_id)

    # Build the system prompt
    system_prompt = _build_group_system_prompt(group_id, grp, context, run_date)

    # Get task prompt
    task_prompt_map = {
        1: "group1_task_pir1.txt",
        2: "group2_task_pir2.txt",
        3: "group3_task_pir3.txt",
        4: "group4_task_pir4.txt",
        5: "group5_task_black_swan.txt",
    }
    task_text = load_task_prompt(task_prompt_map[group_id])

    # Inject PIR text for groups 1-4
    if group_id in (1, 2, 3, 4):
        pir_num = grp["pir"]
        pir_text = load_pir_text(pir_num)
        task_text = task_text.replace(f"{{pir{pir_num}_full_text}}", pir_text)

    # Inject categories for group 2
    if group_id == 2:
        cat_text = "\n".join(
            f"- {cat}" for cat in CATEGORIES_OF_MILITARY_INTERVENTION
        )
        task_text = task_text.replace("{categories_full_text}", cat_text)

    # Create CrewAI Task — the lead agent drives, all agents contribute context
    lead_agent = agents[0]
    crew_task = Task(
        description=system_prompt + "\n\n" + task_text,
        expected_output=(
            "Structured JSON with: group synthesis, trajectory assessment, "
            "ICD 203 confidence level, collection gaps, and per-expert "
            "Tree of Thought branches (A, B, C)."
        ),
        agent=lead_agent,
    )

    # Create and run the Crew
    crew = Crew(
        agents=agents,
        tasks=[crew_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    # Parse output
    output = _parse_crew_output(result)
    output["group_id"] = group_id
    output["group_name"] = grp["name"]
    output["run_date"] = run_date

    logger.info(f"Group {group_id} complete: {len(str(output))} chars output")
    return output


def _run_group_6(
    context: dict,
    prior_outputs: dict,
    run_date: str,
) -> dict:
    """Run Group 6 (Big Question) with Groups 1-5 outputs as extra context."""
    grp = get_group(6)
    agents = get_group_agents(6)

    # Build system prompt
    system_prompt = _build_group_system_prompt(6, grp, context, run_date)

    # Get Big Question task prompt
    task_text = load_task_prompt("group6_task_big_question.txt")

    # Inject Groups 1-5 synthesis outputs
    for prev_id in range(1, 6):
        placeholder = f"{{ae_db{prev_id}_synthesis}}"
        prev_output = prior_outputs.get(prev_id, {})
        if isinstance(prev_output, dict):
            synthesis = prev_output.get("synthesis", prev_output)
            task_text = task_text.replace(
                placeholder, json.dumps(synthesis, indent=2, default=str)
            )
        else:
            task_text = task_text.replace(placeholder, str(prev_output))

    lead_agent = agents[0]
    crew_task = Task(
        description=system_prompt + "\n\n" + task_text,
        expected_output=(
            "Structured JSON with: stabilizing forces assessment, "
            "destabilizing forces assessment, cross-domain propagation map, "
            "structural trajectory with ICD 203 confidence, net assessment "
            "vs. last week, and Black Swan consensus challenge integration."
        ),
        agent=lead_agent,
    )

    crew = Crew(
        agents=agents,
        tasks=[crew_task],
        process=Process.sequential,
        verbose=True,
    )

    result = crew.kickoff()

    output = _parse_crew_output(result)
    output["group_id"] = 6
    output["group_name"] = grp["name"]
    output["run_date"] = run_date

    logger.info(f"Group 6 (Big Question) complete: {len(str(output))} chars output")
    return output


# ── Prompt Assembly ───────────────────────────────────────────────────

def _build_group_system_prompt(
    group_id: int, grp: dict, context: dict, run_date: str
) -> str:
    """
    Assemble the 4-block system prompt for an analysis group.

    Block 0: Mission Directive
    Block 1: Group Identity + ToT Methodology
    Block 2: Expert Personas
    Block 3: Analyst Context Package
    """
    # Block 0: Mission Directive
    block0 = load_task_prompt("mission_directive.txt") + "\n\n"

    # Block 1: Group Identity
    agent_keys = grp["agents"]
    block1 = (
        f"You are a team of {len(agent_keys)} subject matter experts conducting "
        f"a structured intelligence analysis using the Tree of Thought (ToT) "
        f"methodology. Each expert reasons independently across three branches "
        f"before the group synthesizes a unified assessment. ICD 203/206 confidence "
        f"language is mandatory throughout. Audience is O-6 and above.\n\n"
        f"Group: {grp['name']}\n"
        f"Focus: {grp['description']}\n"
        f"Run Date: {run_date}\n\n"
    )

    # Block 2: Expert Personas
    block2 = "YOUR TEAM MEMBERS:\n\n"
    for i, key in enumerate(agent_keys, 1):
        agent_data = AGENT_REGISTRY[key]
        block2 += f"EXPERT {i}: {agent_data['role']}\n"
        block2 += f"{agent_data['backstory']}\n\n"

    # Block 3: Context Package
    block3 = format_context_block(context)

    return block0 + block1 + block2 + block3


# ── Output Handling ───────────────────────────────────────────────────

def _parse_crew_output(result) -> dict:
    """Parse CrewAI crew output into a structured dict."""
    raw = str(result)

    # Try to extract JSON from the output
    try:
        # Look for JSON block in the output
        if "```json" in raw:
            json_start = raw.index("```json") + 7
            json_end = raw.index("```", json_start)
            return json.loads(raw[json_start:json_end].strip())
        elif "{" in raw and "}" in raw:
            # Find outermost braces
            first_brace = raw.index("{")
            last_brace = raw.rindex("}") + 1
            return json.loads(raw[first_brace:last_brace])
    except (json.JSONDecodeError, ValueError):
        pass

    # Return as raw text if not parseable
    return {"raw_output": raw, "synthesis": raw}


def _store_assessment(group_id: int, run_date: str, output: dict):
    """Store group assessment in ae_assessments table."""
    with get_cursor() as cursor:
        cursor.execute(
            """INSERT INTO ae_assessments
                   (group_id, run_date, assessment_json, synthesis_text,
                    trajectory, confidence_level)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                   assessment_json = VALUES(assessment_json),
                   synthesis_text = VALUES(synthesis_text),
                   trajectory = VALUES(trajectory),
                   confidence_level = VALUES(confidence_level)""",
            (
                group_id,
                run_date,
                json.dumps(output, default=str),
                output.get("synthesis", output.get("raw_output", "")),
                output.get("trajectory", ""),
                output.get("confidence_level", ""),
            ),
        )


def _load_prior_group_outputs(run_date: str) -> dict:
    """Load Groups 1-5 outputs from the database for Group 6."""
    outputs = {}
    for gid in range(1, 6):
        rows = execute_query(
            """SELECT assessment_json FROM ae_assessments
               WHERE group_id = %s AND run_date = %s""",
            (gid, run_date),
        )
        if rows and rows[0].get("assessment_json"):
            try:
                outputs[gid] = json.loads(rows[0]["assessment_json"])
            except (json.JSONDecodeError, TypeError):
                outputs[gid] = {"raw_output": rows[0]["assessment_json"]}
    return outputs
