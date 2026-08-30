#!/usr/bin/env python3
"""Validate a digital-human-complete-workflow profile with stdlib only."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PureWindowsPath


STAGES = ("rewrite", "voice", "avatar", "packaging")
ENTRY_MODES = ("full", "from_script", "from_audio", "packaging_only")
REQUIRED_GATES = {
    "lawful_use_declaration": "explicit_user",
    "identity_authorization": "verified_before_media_processing",
    "script_approval": "explicit_user",
    "audio_approval": "explicit_user",
    "avatar_qa": "required",
    "avatar_approval": "explicit_user",
    "packaging_sample": "internal_required",
    "final_delivery_qa": "required",
}
REQUIRED_POLICIES = {
    "distribution_verification": "required_before_onboarding",
    "runtime_preflight": "required_before_stage_execution",
    "end_to_end_ready_claim": "only_after_all_stage_checks",
    "first_run_onboarding": "required_local_status",
    "asset_center": "local_profile_index",
    "task_order": "required_for_every_run",
    "cross_stage_handoff": "path_hash_no_copy_paste",
    "estimate_before_stage_or_retry": "required",
    "user_facing_estimate": "simple_stage_range",
    "feedback_logs": "per_module_scoped",
    "offline_behavior": "show_network_issue_disable_generation",
    "quality_semantics": "needs_optimization_not_broken",
    "project_change_semantics": "needs_update_preserve_history",
    "material_collection": "disclose_all_collect_by_stage",
    "profile_reuse": "persistent_until_recalibration_required",
    "module_activation": "independent_by_entry",
    "voice_style_confirmation_scope": "once_per_valid_voice_profile",
    "voice_style_reprompt_each_project": False,
    "intake_disclosure": "full_requirements_upfront_by_entry",
    "third_party_identity": "verified_consent_required",
    "prohibited_use_handling": "stop_and_record",
    "maintainer_mode": "local_open_source_no_uploads_by_default",
    "creator_profile": "quick_or_pro",
    "voice_calibration": "three_style_first_confirmation",
    "pronunciation_research": "chinese_context_online_required",
    "avatar_capture": "pre_recording_brief_then_mouth_only_qa",
    "sensitive_data_storage": "local_private_by_default",
    "packaging_layout_selection": "disabled",
    "packaging_canvas": "1080x1920",
    "packaging_person_position": "bottom_right",
    "packaging_cover": "required",
    "generated_content_disclosure": "required",
}
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate(profile: object) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(profile, dict):
        return ["Profile root must be a JSON object."], warnings

    if profile.get("schema_version") != 1:
        errors.append("schema_version must be 1.")

    profile_id = profile.get("profile_id")
    if not isinstance(profile_id, str) or not SKILL_NAME.fullmatch(profile_id):
        errors.append("profile_id must use lowercase letters, digits, and hyphens.")

    if profile.get("stage_execution") != "serial":
        errors.append("stage_execution must be 'serial'.")

    entry_modes = profile.get("entry_modes")
    if entry_modes != list(ENTRY_MODES):
        errors.append(
            "entry_modes must contain full, from_script, from_audio, and packaging_only in that order."
        )

    stage_skills = profile.get("stage_skills")
    if not isinstance(stage_skills, dict):
        errors.append("stage_skills must be an object.")
    else:
        for stage in STAGES:
            config = stage_skills.get(stage)
            if not isinstance(config, dict):
                errors.append(f"stage_skills.{stage} must be an object.")
                continue
            skill = config.get("skill")
            if not isinstance(skill, str) or not SKILL_NAME.fullmatch(skill):
                errors.append(
                    f"stage_skills.{stage}.skill must be a valid skill name."
                )
            elif skill.startswith("your-"):
                warnings.append(
                    f"stage_skills.{stage}.skill is an example binding; replace it before a real run."
                )

    gates = profile.get("gates")
    if not isinstance(gates, dict):
        errors.append("gates must be an object.")
    else:
        for key, expected in REQUIRED_GATES.items():
            if gates.get(key) != expected:
                errors.append(f"gates.{key} must be '{expected}'.")

    policies = profile.get("policies")
    if not isinstance(policies, dict):
        errors.append("policies must be an object.")
    else:
        for key, expected in REQUIRED_POLICIES.items():
            if policies.get(key) != expected:
                errors.append(f"policies.{key} must be {expected!r}.")

    integrity = profile.get("artifact_integrity")
    if not isinstance(integrity, dict) or integrity.get("algorithm") != "sha256":
        errors.append("artifact_integrity.algorithm must be 'sha256'.")

    paths = profile.get("paths")
    if not isinstance(paths, dict):
        errors.append("paths must be an object.")
    else:
        for key in ("project_root", "delivery_root"):
            value = paths.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"paths.{key} must be a non-empty string.")
            elif Path(value).is_absolute() or PureWindowsPath(value).is_absolute():
                warnings.append(
                    f"paths.{key} is absolute; keep machine-specific paths in an uncommitted local profile."
                )

    privacy = profile.get("privacy")
    required_private_flags = (
        "commit_identity_assets",
        "commit_reference_voice",
        "commit_secrets",
    )
    if not isinstance(privacy, dict):
        errors.append("privacy must be an object.")
    else:
        for key in required_private_flags:
            if privacy.get(key) is not False:
                errors.append(f"privacy.{key} must be false.")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()

    try:
        raw = args.profile.read_text(encoding="utf-8")
        profile = json.loads(raw)
    except FileNotFoundError:
        print(f"ERROR: profile not found: {args.profile}", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read profile: {exc}", file=sys.stderr)
        return 2

    errors, warnings = validate(profile)
    for warning in warnings:
        print(f"WARNING: {warning}")
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1

    print(f"PASS: profile schema is valid ({len(warnings)} warning(s)).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
