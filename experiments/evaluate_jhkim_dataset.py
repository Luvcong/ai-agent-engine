from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError
from opik import Opik, track
from opik.evaluation import evaluate

from app.agents.medical import get_medical_agent
from app.core.config import settings
from app.observability.opik import configure_opik, create_opik_tracer
from experiments.opik_metrics import (
    FINAL_RESPONSE_TOOL_NAMES,
    ClarificationNeedAccuracy,
    ResponseGoalMatch,
    ToolSelectionAccuracy,
)


def _int_env(name: str, default: int | None) -> int | None:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _normalize_litellm_model_name(model_name: str | None) -> str | None:
    if model_name is None:
        return None
    stripped = model_name.strip()
    if not stripped:
        return None
    if "/" in stripped:
        return stripped
    # GEval uses LiteLLM under the hood, which expects a provider-qualified model name.
    return f"openai/{stripped}"


def _resolve_judge_temperature(
    judge_model: str | None,
    explicit_temperature: float | None,
) -> float:
    if explicit_temperature is not None:
        return explicit_temperature
    normalized = (judge_model or "").lower()
    if "gpt-5" in normalized:
        return 1.0
    return 0.0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the Opik dataset `jhkim-dataset` with three custom metrics."
    )
    parser.add_argument(
        "--dataset-name",
        default=os.getenv("OPIK_EVAL_DATASET_NAME", "jhkim-dataset"),
    )
    parser.add_argument(
        "--experiment-name",
        default=os.getenv("OPIK_EVAL_EXPERIMENT_NAME", "jhkim-dataset-eval"),
    )
    parser.add_argument("--project-name", default=os.getenv("OPIK_PROJECT_NAME"))
    parser.add_argument("--judge-model", default=os.getenv("OPIK_EVAL_MODEL", settings.OPENAI_MODEL))
    parser.add_argument(
        "--judge-temperature",
        type=float,
        default=(
            float(os.getenv("OPIK_EVAL_JUDGE_TEMPERATURE"))
            if os.getenv("OPIK_EVAL_JUDGE_TEMPERATURE") not in (None, "")
            else None
        ),
    )
    parser.add_argument(
        "--agent-model",
        default=os.getenv("OPIK_EVAL_AGENT_MODEL", settings.OPENAI_MODEL),
    )
    parser.add_argument("--nb-samples", type=int, default=_int_env("OPIK_EVAL_NB_SAMPLES", None))
    parser.add_argument("--task-threads", type=int, default=_int_env("OPIK_EVAL_TASK_THREADS", 4))
    parser.add_argument(
        "--recursion-limit",
        type=int,
        default=_int_env("OPIK_EVAL_RECURSION_LIMIT", settings.DEEPAGENT_RECURSION_LIMIT),
    )
    parser.add_argument("--input-key", default=os.getenv("OPIK_EVAL_INPUT_KEY", "input"))
    parser.add_argument(
        "--expected-tools-key",
        default=os.getenv("OPIK_EVAL_EXPECTED_TOOLS_KEY", "expected_tool"),
    )
    parser.add_argument(
        "--clarification-needed-key",
        default=os.getenv("OPIK_EVAL_CLARIFICATION_KEY", "should_ask_clarification"),
    )
    parser.add_argument(
        "--response-goal-key",
        default=os.getenv("OPIK_EVAL_RESPONSE_GOAL_KEY", "expected_output"),
    )
    return parser.parse_args()


def _get_value(item: dict[str, Any], key: str) -> Any:
    current: Any = item
    for part in key.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _message_content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if text:
                    parts.append(str(text))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(part.strip() for part in parts if part and part.strip())
    return str(content).strip()


def _extract_final_output(result: dict[str, Any]) -> str:
    structured_response = result.get("structured_response")
    if structured_response is not None:
        content = getattr(structured_response, "content", None)
        if content:
            return str(content).strip()

    for message in reversed(result.get("messages", [])):
        tool_calls = getattr(message, "tool_calls", None)
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call.get("name") in FINAL_RESPONSE_TOOL_NAMES:
                    content = tool_call.get("args", {}).get("content")
                    if content:
                        return str(content).strip()

        content = _message_content_to_text(getattr(message, "content", None))
        if content:
            return content

    return ""


def _extract_tool_calls(result: dict[str, Any]) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for message in result.get("messages", []):
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            continue
        for tool_call in tool_calls:
            name = tool_call.get("name")
            if not name or name in FINAL_RESPONSE_TOOL_NAMES:
                continue
            extracted.append(
                {
                    "function_name": name,
                    "function_parameters": tool_call.get("args", {}),
                }
            )
    return extracted


def _build_evaluation_task(args: argparse.Namespace):
    agent = get_medical_agent()

    @track(name="jhkim_dataset_eval_task")
    def evaluation_task(dataset_item: dict[str, Any]) -> dict[str, Any]:
        user_input = str(_get_value(dataset_item, args.input_key) or "")
        expected_tools = _get_value(dataset_item, args.expected_tools_key)
        clarification_needed = _get_value(dataset_item, args.clarification_needed_key)
        response_goal = _get_value(dataset_item, args.response_goal_key)

        thread_id = str(uuid.uuid4())
        tracer = create_opik_tracer(thread_id)
        config = {
            "configurable": {"thread_id": thread_id},
            "recursion_limit": args.recursion_limit,
        }
        if tracer is not None:
            config["callbacks"] = [tracer]

        try:
            try:
                result = asyncio.run(
                    agent.ainvoke(
                        {"messages": [HumanMessage(content=user_input)]},
                        config=config,
                    )
                )
            except GraphRecursionError:
                retry_limit = max(args.recursion_limit + 20, args.recursion_limit * 2)
                retry_config = {
                    "configurable": {"thread_id": thread_id},
                    "recursion_limit": retry_limit,
                }
                if tracer is not None:
                    retry_config["callbacks"] = [tracer]
                try:
                    result = asyncio.run(
                        agent.ainvoke(
                            {"messages": [HumanMessage(content=user_input)]},
                            config=retry_config,
                        )
                    )
                except GraphRecursionError as exc:
                    return {
                        "input": user_input,
                        "output": "",
                        "expected_tools": expected_tools,
                        "clarification_needed": clarification_needed,
                        "response_goal": response_goal,
                        "actual_tool_calls": [],
                        "execution_error": f"graph_recursion_error(limit={retry_limit}): {exc}",
                    }
        finally:
            if tracer is not None:
                tracer.flush()

        return {
            "input": user_input,
            "output": _extract_final_output(result),
            "expected_tools": expected_tools,
            "clarification_needed": clarification_needed,
            "response_goal": response_goal,
            "actual_tool_calls": _extract_tool_calls(result),
        }

    return evaluation_task


def main() -> None:
    args = _parse_args()
    configure_opik()
    judge_model = _normalize_litellm_model_name(args.judge_model)
    judge_temperature = _resolve_judge_temperature(
        judge_model=judge_model,
        explicit_temperature=args.judge_temperature,
    )
    settings.OPENAI_MODEL = args.agent_model

    client = Opik()
    dataset = client.get_dataset(name=args.dataset_name)

    metrics = [
        ToolSelectionAccuracy(project_name=args.project_name),
        ClarificationNeedAccuracy(
            judge_model=judge_model,
            judge_temperature=judge_temperature,
            project_name=args.project_name,
        ),
        ResponseGoalMatch(
            judge_model=judge_model,
            judge_temperature=judge_temperature,
            project_name=args.project_name,
        ),
    ]

    result = evaluate(
        dataset=dataset,
        task=_build_evaluation_task(args),
        scoring_metrics=metrics,
        experiment_name=args.experiment_name,
        project_name=args.project_name,
        nb_samples=args.nb_samples,
        task_threads=args.task_threads,
    )

    print(
        json.dumps(
            {
                "dataset_name": args.dataset_name,
                "experiment_name": args.experiment_name,
                "project_name": args.project_name,
                "agent_model": args.agent_model,
                "judge_model": judge_model,
                "judge_temperature": judge_temperature,
                "recursion_limit": args.recursion_limit,
                "result": str(result),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
