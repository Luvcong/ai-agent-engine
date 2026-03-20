from __future__ import annotations

import json
from typing import Any

from opik.evaluation.metrics import BaseMetric, GEval, score_result
from opik.message_processing.emulation.models import SpanModel

FINAL_RESPONSE_TOOL_NAMES = {"AgentResponse", "ChatResponse"}


def _normalize_expected_tools(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.lower() in {"none", "null", "no_tool", "no-tool"}:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                normalized = [
                    str(item).strip()
                    for item in parsed
                    if str(item).strip()
                    and str(item).strip().lower() not in {"none", "null", "no_tool", "no-tool"}
                ]
                return normalized
        if "," in stripped:
            return [
                item.strip()
                for item in stripped.split(",")
                if item.strip() and item.strip().lower() not in {"none", "null", "no_tool", "no-tool"}
            ]
        return [stripped]
    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
            and str(item).strip().lower() not in {"none", "null", "no_tool", "no-tool"}
        ]
    return [str(value).strip()]


def _normalize_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n"}:
        return False
    return None


def _collect_tool_names(span: SpanModel) -> list[str]:
    tool_names: list[str] = []

    def _walk(current: SpanModel) -> None:
        if current.type == "tool" and current.name and current.name not in FINAL_RESPONSE_TOOL_NAMES:
            tool_names.append(current.name)
        for child in current.spans:
            _walk(child)

    _walk(span)
    return tool_names


def _collect_tool_names_from_task_output(tool_calls: Any) -> list[str]:
    if not isinstance(tool_calls, list):
        return []
    tool_names: list[str] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        name = tool_call.get("function_name") or tool_call.get("name")
        if name and name not in FINAL_RESPONSE_TOOL_NAMES:
            tool_names.append(str(name))
    return tool_names


class ToolSelectionAccuracy(BaseMetric):
    def __init__(
        self,
        name: str = "tool_selection_accuracy",
        track: bool = True,
        project_name: str | None = None,
    ) -> None:
        super().__init__(name=name, track=track, project_name=project_name)

    def score(
        self,
        expected_tools: Any,
        task_span: SpanModel | None = None,
        actual_tool_calls: Any = None,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        expected = _normalize_expected_tools(expected_tools)
        actual = _collect_tool_names(task_span) if task_span is not None else []
        if not actual:
            actual = _collect_tool_names_from_task_output(actual_tool_calls)

        if not expected:
            value = 1.0 if not actual else 0.0
            reason = (
                "No tool was expected and no tool was used."
                if value == 1.0
                else f"No tool was expected, but the agent used: {actual}"
            )
            return score_result.ScoreResult(
                name=self.name,
                value=value,
                reason=reason,
                metadata={"expected_tools": expected, "actual_tools": actual},
            )

        if not actual:
            return score_result.ScoreResult(
                name=self.name,
                value=0.0,
                reason=f"Expected one of {expected}, but the agent did not call a tool.",
                metadata={"expected_tools": expected, "actual_tools": actual},
            )

        matched_tools = [tool for tool in actual if tool in expected]
        value = 1.0 if matched_tools else 0.0
        reason = (
            f"Expected tool found in call chain: {matched_tools[0]}"
            if value == 1.0
            else f"Expected one of {expected} in tool call chain, but got {actual}."
        )
        return score_result.ScoreResult(
            name=self.name,
            value=value,
            reason=reason,
            metadata={
                "expected_tools": expected,
                "actual_tools": actual,
                "matched_tools": matched_tools,
            },
        )


class ClarificationNeedAccuracy(BaseMetric):
    def __init__(
        self,
        name: str = "clarification_need_accuracy",
        judge_model: str | None = None,
        judge_temperature: float = 0.0,
        track: bool = True,
        project_name: str | None = None,
    ) -> None:
        super().__init__(name=name, track=track, project_name=project_name)
        self._judge = GEval(
            name=f"{name}_judge",
            task_introduction=(
                "Judge whether the assistant handled clarification needs correctly."
            ),
            evaluation_criteria=(
                "Use the JSON payload. `expected_clarification_needed` is the ground-truth label. "
                "Return 10 only if the assistant behavior matches that label exactly. "
                "If clarification was needed, the assistant should explicitly ask for the missing detail "
                "instead of guessing. If clarification was not needed, the assistant should answer directly "
                "without unnecessary follow-up questions. Return 0 otherwise. "
                "Write the scoring reason in Korean."
            ),
            model=judge_model,
            temperature=judge_temperature,
            track=False,
        )

    def score(
        self,
        input: str,
        output: str,
        clarification_needed: Any,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        expected = _normalize_bool(clarification_needed)
        if expected is None:
            return score_result.ScoreResult(
                name=self.name,
                value=0.0,
                reason="`clarification_needed` must be a boolean-like value.",
                metadata={"clarification_needed": clarification_needed},
                scoring_failed=True,
            )

        payload = json.dumps(
            {
                "user_input": input,
                "assistant_output": output,
                "expected_clarification_needed": expected,
            },
            ensure_ascii=False,
            indent=2,
        )
        judged = self._judge.score(output=payload)
        return score_result.ScoreResult(
            name=self.name,
            value=judged.value,
            reason=judged.reason,
            metadata={"expected_clarification_needed": expected},
        )


class ResponseGoalMatch(BaseMetric):
    def __init__(
        self,
        name: str = "response_goal_match",
        judge_model: str | None = None,
        judge_temperature: float = 0.0,
        track: bool = True,
        project_name: str | None = None,
    ) -> None:
        super().__init__(name=name, track=track, project_name=project_name)
        self._judge = GEval(
            name=f"{name}_judge",
            task_introduction=(
                "Judge whether the assistant's final answer matches the intended response goal."
            ),
            evaluation_criteria=(
                "Use the JSON payload. `response_goal` describes what the answer should accomplish. "
                "Return 10 only if the assistant output directly fulfills that goal in a materially correct way. "
                "Return 0 if it misses the goal, answers a different question, is overly vague, "
                "or contradicts the requested goal. "
                "Write the scoring reason in Korean."
            ),
            model=judge_model,
            temperature=judge_temperature,
            track=False,
        )

    def score(
        self,
        input: str,
        output: str,
        response_goal: Any,
        **ignored_kwargs: Any,
    ) -> score_result.ScoreResult:
        payload = json.dumps(
            {
                "user_input": input,
                "assistant_output": output,
                "response_goal": response_goal,
            },
            ensure_ascii=False,
            indent=2,
        )
        judged = self._judge.score(output=payload)
        return score_result.ScoreResult(
            name=self.name,
            value=judged.value,
            reason=judged.reason,
            metadata={"response_goal": response_goal},
        )
