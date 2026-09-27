"""Skill catalog on disk.

The LLM router asks the LLM which skills to mount. The openJev router asks
openJev. Either way the catalog fields are name, description, tier, and the
role a function or agent skill belongs to. The caller's role is context for
that choice. It is not a key that assigns a fixed stack. Synthesis stays on
the LLM.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from kp.config import get_settings
from kp.knowledge.intent import jev_systemone, load_skill
from kp.llm import CloudKeyRequired, build_openai_compatible_client

# openJev yes/no scores near 0.5 are ties. A skill is mounted when yes is clearly ahead.
SKILL_YES_MIN_PROBABILITY = 0.6


class SkillSelectorRequired(RuntimeError):
    """A knowledge ask needs the LLM skill selector and no key is configured."""


@dataclass(frozen=True)
class SkillInfo:
    id: str
    name: str
    description: str
    tier: str
    role: str | None
    relative: str


@dataclass(frozen=True)
class SkillStack:
    sources: list[str]
    directories: list[str]
    names: list[str]


def _skill_dirs(parent: Path) -> list[Path]:
    if not parent.is_dir():
        return []
    found = []
    for child in sorted(parent.iterdir(), key=lambda path: path.name):
        if child.is_dir() and (child / "SKILL.md").is_file():
            found.append(child)
    return found


def _safe_skill_id(skill_id: str) -> bool:
    if not skill_id or skill_id in {".", ".."}:
        return False
    return "/" not in skill_id and "\\" not in skill_id and Path(skill_id).name == skill_id


def _add(found: list[SkillInfo], root: Path, path: Path, tier: str, role: str | None) -> None:
    meta = load_skill(path / "SKILL.md")
    found.append(
        SkillInfo(
            id=path.name,
            name=meta.get("name") or path.name,
            description=meta.get("description") or "",
            tier=tier,
            role=role,
            relative=path.relative_to(root).as_posix(),
        )
    )


def skill_catalog(skills_root: Path | None = None) -> list[SkillInfo]:
    """Every SKILL.md under the catalog, with metadata and no instruction body."""
    root = skills_root or get_settings().skills_root
    found: list[SkillInfo] = []
    for child in _skill_dirs(root / "foundational"):
        _add(found, root, child, "foundational", None)
    functions = root / "functions"
    if functions.is_dir():
        for role_dir in sorted((path for path in functions.iterdir() if path.is_dir()), key=lambda path: path.name):
            for child in _skill_dirs(role_dir):
                _add(found, root, child, "function", role_dir.name)
    agents = root / "agents"
    if agents.is_dir():
        for role_dir in sorted((path for path in agents.iterdir() if path.is_dir()), key=lambda path: path.name):
            for child in _skill_dirs(role_dir):
                _add(found, root, child, "agent", role_dir.name)
    for child in _skill_dirs(root / "users"):
        _add(found, root, child, "user", None)
    return found


def catalog_metadata(catalog: list[SkillInfo]) -> list[dict]:
    """Fields the selector is allowed to see. Instruction bodies stay on disk."""
    rows = []
    for skill in catalog:
        row = {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "tier": skill.tier,
        }
        if skill.tier in {"function", "agent"}:
            row["role"] = skill.role
        rows.append(row)
    return rows


def _index(catalog: list[SkillInfo]) -> dict[str, str]:
    by_key: dict[str, str] = {}
    for skill in catalog:
        by_key.setdefault(skill.id, skill.id)
        by_key.setdefault(skill.name, skill.id)
    return by_key


def accept_skill_ids(raw_ids: list[str], catalog: list[SkillInfo]) -> list[str]:
    """Keep catalog ids, in the selector's order. Unknown ids are dropped."""
    by_key = _index(catalog)
    chosen: list[str] = []
    seen: set[str] = set()
    for raw in raw_ids:
        skill_id = str(raw).strip()
        if not _safe_skill_id(skill_id):
            continue
        canonical = by_key.get(skill_id)
        if canonical is None or canonical in seen:
            continue
        seen.add(canonical)
        chosen.append(canonical)
    return chosen


def mount_skills(skill_ids: list[str], skills_root: Path | None = None) -> SkillStack:
    """Mount only the selected catalog skills. Role does not filter this list."""
    catalog = skill_catalog(skills_root)
    selected = accept_skill_ids(skill_ids, catalog)
    by_id = {skill.id: skill for skill in catalog}
    sources: list[str] = []
    directories: list[str] = []
    names: list[str] = []
    seen_sources: set[str] = set()
    for skill_id in selected:
        skill = by_id[skill_id]
        directories.append(skill.relative)
        names.append(skill.id)
        parent = f"/skills/{Path(skill.relative).parent.as_posix()}/"
        if parent not in seen_sources:
            seen_sources.add(parent)
            sources.append(parent)
    return SkillStack(sources=sources, directories=directories, names=names)


def skill_bodies(skill_ids: list[str], skills_root: Path | None = None) -> str:
    root = skills_root or get_settings().skills_root
    mounted = mount_skills(skill_ids, root)
    parts = []
    for relative in mounted.directories:
        parts.append(load_skill(root / relative / "SKILL.md")["body"])
    return "\n\n".join(parts)


def _parse_skill_ids(content: str) -> list[str]:
    match = re.search(r"\{.*\}", content, re.S)
    if not match:
        raise SkillSelectorRequired("Skill selection did not return skill ids")
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise SkillSelectorRequired("Skill selection did not return skill ids") from exc
    raw = payload.get("skill_ids")
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise SkillSelectorRequired("Skill selection did not return skill ids")
    return raw


def select_skills(question: str, role: str) -> list[str]:
    """Ask the LLM which catalog skills to mount. Tests may replace this function."""
    try:
        client = build_openai_compatible_client()
    except CloudKeyRequired as exc:
        raise SkillSelectorRequired("LLM_API_KEY is required to select skills for a knowledge ask") from exc
    catalog = skill_catalog()
    prompt = json.dumps(
        {
            "role": role,
            "question": question,
            "skills": catalog_metadata(catalog),
        }
    )
    try:
        body = client.chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Choose which skills to mount for this question. "
                        "The role is context, not a filter that assigns a fixed set. "
                        "Return JSON with a skill_ids array using only catalog ids."
                    ),
                },
                {"role": "user", "content": prompt},
            ]
        )
    except httpx.HTTPError as exc:
        raise SkillSelectorRequired("Skill selection failed: the LLM request did not succeed") from exc
    content = body["choices"][0]["message"]["content"]
    return accept_skill_ids(_parse_skill_ids(content), catalog)


def select_skills_with_jev(question: str, role: str) -> list[str]:
    """Ask openJev which catalog skills to mount. Synthesis does not use this call."""
    catalog = skill_catalog()
    questions = {}
    for skill in catalog:
        description = (skill.description or skill.name).strip()
        questions[skill.id] = {
            "type": "choice",
            "instructions": (
                f"Should the skill {skill.name} be mounted for this question? "
                f"The role {role} is context, not a fixed assignment. Tier: {skill.tier}."
            ),
            "criteria": {
                "yes": description[:180],
                "no": "This skill does not apply to the question.",
            },
        }
    parsed = jev_systemone(f"Role: {role}\nUser: {question}", questions)
    answers = parsed.get("answers") or {}
    chosen: list[str] = []
    for skill in catalog:
        answer = answers.get(skill.id) or {}
        if answer.get("choice") != "yes":
            continue
        probability = (answer.get("probabilities") or {}).get("yes")
        if isinstance(probability, (int, float)) and probability >= SKILL_YES_MIN_PROBABILITY:
            chosen.append(skill.id)
    if chosen:
        return chosen
    best_id = ""
    best_probability = -1.0
    for skill in catalog:
        answer = answers.get(skill.id) or {}
        probability = (answer.get("probabilities") or {}).get("yes")
        if answer.get("choice") != "yes" or not isinstance(probability, (int, float)):
            continue
        if probability > best_probability:
            best_id = skill.id
            best_probability = probability
    if best_id:
        return [best_id]
    # Every catalog skill was "no". None of them is a revenue or chart skill,
    # so a chart of company performance must still answer from retrieved records.
    return []
