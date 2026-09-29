from __future__ import annotations

from dataclasses import dataclass
import re

from .cypher_core import ModelRoles, RoutingDecision, select_route


MAX_MODEL_STAGES = 3
HANDOFF_FIELDS = (
    "task_summary",
    "constraints",
    "evidence_references",
    "open_questions",
    "proposed_result",
)


@dataclass(frozen=True)
class ModelStage:
    stage_id: str
    purpose: str
    route: RoutingDecision
    consumes: tuple[str, ...]
    produces: tuple[str, ...]


@dataclass(frozen=True)
class ModelWorkflow:
    stages: tuple[ModelStage, ...]
    sequential_models: bool
    parallel_tools_allowed: bool
    raw_reasoning_handoff: bool
    authority_source: str

    def public_summary(self) -> dict[str, object]:
        return {
            "stage_count": len(self.stages),
            "sequential_models": self.sequential_models,
            "parallel_tools_allowed": self.parallel_tools_allowed,
            "raw_reasoning_handoff": self.raw_reasoning_handoff,
            "authority_source": self.authority_source,
            "stages": [
                {
                    "stage_id": stage.stage_id,
                    "purpose": stage.purpose,
                    "profile": stage.route.profile,
                    "model": stage.route.model,
                    "consumes": list(stage.consumes),
                    "produces": list(stage.produces),
                }
                for stage in self.stages
            ],
        }


def _explicit_cross_check(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.casefold())
    markers = (
        "cross-check with another model",
        "cross check with another model",
        "use multiple models",
        "use all three models",
        "second model review",
        "independent model review",
    )
    return any(marker in normalized for marker in markers)


def _stage(
    stage_id: str,
    purpose: str,
    route: RoutingDecision,
    *,
    consumes: tuple[str, ...] = (),
    produces: tuple[str, ...] = HANDOFF_FIELDS,
) -> ModelStage:
    return ModelStage(stage_id, purpose, route, consumes, produces)


def plan_model_workflow(
    text: str,
    *,
    has_image: bool = False,
    requested_mode: str = "auto",
    model_roles: ModelRoles | None = None,
) -> ModelWorkflow:
    """Create a bounded model plan. It grants no tools or execution permission."""

    roles = model_roles or ModelRoles()
    primary = select_route(
        text,
        requested_mode,
        has_image=has_image,
        model_roles=roles,
    )
    stages: list[ModelStage] = []

    if has_image:
        stages.append(
            _stage(
                "observe",
                "Extract task-relevant visual facts; do not infer permissions or actions.",
                primary,
                produces=("evidence_references", "task_summary", "open_questions"),
            )
        )
        synthesis = select_route(
            text,
            "deep" if len(text) >= 800 or _explicit_cross_check(text) else "fast",
            model_roles=roles,
        )
        stages.append(
            _stage(
                "synthesize",
                "Answer from the bounded visual evidence and current task constraints.",
                synthesis,
                consumes=("evidence_references", "task_summary", "open_questions"),
                produces=("proposed_result", "open_questions"),
            )
        )
    elif _explicit_cross_check(text):
        fast = select_route(text, "fast", model_roles=roles)
        deep = select_route(text, "deep", model_roles=roles)
        stages.extend(
            (
                _stage(
                    "brief",
                    "Create a concise structured task brief and identify constraints.",
                    fast,
                    produces=("task_summary", "constraints", "open_questions"),
                ),
                _stage(
                    "solve",
                    "Perform the difficult reasoning using the task brief and verified evidence.",
                    deep,
                    consumes=("task_summary", "constraints", "evidence_references", "open_questions"),
                    produces=("proposed_result", "open_questions"),
                ),
                _stage(
                    "compliance_review",
                    "Check instruction coverage and clearly identify unresolved claims.",
                    fast,
                    consumes=("task_summary", "constraints", "proposed_result", "evidence_references"),
                    produces=("proposed_result", "open_questions"),
                ),
            )
        )
    else:
        stages.append(
            _stage(
                "respond",
                "Handle the request with the selected measured role.",
                primary,
                produces=("proposed_result", "open_questions"),
            )
        )

    if not stages or len(stages) > MAX_MODEL_STAGES:
        raise ValueError("Model workflow must contain between one and three stages")
    return ModelWorkflow(
        stages=tuple(stages),
        sequential_models=True,
        parallel_tools_allowed=True,
        raw_reasoning_handoff=False,
        authority_source="deterministic host policy and approved capabilities",
    )
