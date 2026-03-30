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

    # Create per-agent branch tasks + final synthesis task
    tasks = []

    # Each expert produces their 3 ToT branches independently
    for i, agent in enumerate(agents[:-1]):  # All but last
        branch_task = Task(
            description=(
                f"{system_prompt}\n\n{task_text}\n\n"
                f"You are Expert {i+1}. Produce your THREE independent "
                f"reasoning branches (A: Conservative, B: Most Likely, "
                f"C: High-Impact Outlier) based on the context above. "
                f"Be specific, cite evidence, and use ICD 203 confidence language."
            ),
            expected_output=(
                f"Expert {i+1} Tree of Thought branches: "
                f"branch_a (conservative), branch_b (most likely), "
                f"branch_c (high-impact outlier), each 2-3 paragraphs."
            ),
            agent=agent,
        )
        tasks.append(branch_task)

    # Final agent synthesizes all branches into the group output
    synthesis_task = Task(
        description=(
            f"{system_prompt}\n\n{task_text}\n\n"
            f"You are the synthesis lead. Review all expert branches above "
            f"and produce the UNIFIED GROUP ASSESSMENT as structured JSON. "
            f"Integrate all expert perspectives, resolve disagreements, "
            f"and produce the final trajectory and confidence assessment."
        ),
        expected_output=(
            "Structured JSON with: group synthesis, trajectory assessment, "
            "ICD 203 confidence level, collection gaps, and per-expert "
            "Tree of Thought branches (A, B, C)."
        ),
        agent=agents[-1],
        context=tasks,  # Feed all branch outputs as context
    )
    tasks.append(synthesis_task)

    crew = Crew(
        agents=agents,
        tasks=tasks,
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

    # Per-agent branch tasks + synthesis (same pattern as Groups 1-5)
    tasks = []
    for i, agent in enumerate(agents[:-1]):
        branch_task = Task(
            description=(
                f"{system_prompt}\n\n{task_text}\n\n"
                f"You are Expert {i+1}. Produce your THREE independent "
                f"meta-synthesis branches: A (dominant stabilizing forces), "
                f"B (dominant destabilizing forces), C (net trajectory and "
                f"cross-domain propagation). Cite evidence from all 5 groups."
            ),
            expected_output=(
                f"Expert {i+1} meta-synthesis branches with cross-group "
                f"integration and structural trajectory assessment."
            ),
            agent=agent,
        )
        tasks.append(branch_task)

    synthesis_task = Task(
        description=(
            f"{system_prompt}\n\n{task_text}\n\n"
            f"You are the synthesis lead for the Big Question. "
            f"Integrate all expert meta-synthesis branches above into "
            f"the FINAL structured JSON answering the Big Question."
        ),
        expected_output=(
            "Structured JSON with: stabilizing forces assessment, "
            "destabilizing forces assessment, cross-domain propagation map, "
            "structural trajectory with ICD 203 confidence, net assessment "
            "vs. last week, and Black Swan consensus challenge integration."
        ),
        agent=agents[-1],
        context=tasks,
    )
    tasks.append(synthesis_task)

    crew = Crew(
        agents=agents,
        tasks=tasks,
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
    """Parse CrewAI crew output into a structured dict.

    Tries multiple extraction strategies:
    1. Fenced JSON block (```json ... ```)
    2. Outermost JSON object { ... }
    3. Outermost JSON array [ ... ]
    4. Falls back to raw text with synthesis key
    """
    raw = str(result)

    # Strategy 1: Fenced JSON block
    if "```json" in raw:
        try:
            json_start = raw.index("```json") + 7
            json_end = raw.index("```", json_start)
            return json.loads(raw[json_start:json_end].strip())
        except (json.JSONDecodeError, ValueError):
            pass

    # Strategy 2: Find outermost JSON object
    if "{" in raw and "}" in raw:
        first = raw.index("{")
        last = raw.rindex("}")
        if last > first:
            try:
                return json.loads(raw[first:last + 1])
            except json.JSONDecodeError:
                pass

    # Strategy 3: Find outermost JSON array
    if "[" in raw and "]" in raw:
        first = raw.index("[")
        last = raw.rindex("]")
        if last > first:
            try:
                arr = json.loads(raw[first:last + 1])
                return {"items": arr, "synthesis": raw}
            except json.JSONDecodeError:
                pass

    # Strategy 4: Raw text fallback — extract synthesis from prose
    logger.warning(
        f"Could not parse JSON from crew output ({len(raw)} chars). "
        f"Storing as raw text."
    )
    return {"raw_output": raw[:50000], "synthesis": raw[:10000]}


def _store_assessment(group_id: int, run_date: str, output: dict):
    """Store group assessment in ae_assessments table."""
    # Extract synthesis — Group 6 uses 'big_question_answer', others use 'synthesis'
    synthesis = (
        output.get("synthesis")
        or output.get("big_question_answer")
        or output.get("raw_output", "")
    )
    # Truncate to avoid DB bloat but keep enough for analysis
    if isinstance(synthesis, dict):
        synthesis = json.dumps(synthesis, default=str)
    synthesis = str(synthesis)[:50000]

    assessment_json = json.dumps(output, default=str)

    logger.info(
        f"Storing Group {group_id} assessment: "
        f"{len(assessment_json)} chars JSON, "
        f"trajectory={output.get('trajectory', '?')}"
    )

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
                assessment_json,
                synthesis,
                output.get("trajectory", output.get("structural_trajectory", "")),
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
