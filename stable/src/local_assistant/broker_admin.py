from __future__ import annotations

import argparse
import json
from pathlib import Path

from .action_broker import ActionStateStore, ApprovedActionEngine
from .broker_mcp import default_audit_path, default_state_path
from .capability_broker import BrokerPolicyViolation, ReadOnlyCapabilityBroker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Human-side approval and undo for the sandbox broker")
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--state", type=Path, default=default_state_path())
    parser.add_argument("--audit", type=Path, default=default_audit_path())
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    show = subparsers.add_parser("show")
    show.add_argument("plan_id")
    approve = subparsers.add_parser("approve")
    approve.add_argument("plan_id")
    undo = subparsers.add_parser("undo")
    undo.add_argument("operation_id")
    return parser


def display_plan(engine: ApprovedActionEngine, plan_id: str) -> None:
    plan = engine.state.get_plan(plan_id)
    if plan.root != str(engine.broker.root):
        raise BrokerPolicyViolation("Plan belongs to a different sandbox root")
    public = engine.public_plan(plan)
    print(json.dumps(public, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    broker = ReadOnlyCapabilityBroker(arguments.root, arguments.audit)
    engine = ApprovedActionEngine(broker, ActionStateStore(arguments.state))
    try:
        if arguments.command == "list":
            plans = engine.state.list_plans(broker.root)
            for plan in plans:
                window = (
                    f"execute_until={plan.approved_expires_at}"
                    if plan.approved_expires_at
                    else f"review_until={plan.expires_at}"
                )
                print(
                    f"{plan.plan_id}  {plan.status:9}  {plan.kind:15}  "
                    f"code={plan.fingerprint[-8:]}  {window}"
                )
            if not plans:
                print("No plans found for this sandbox.")
        elif arguments.command == "show":
            display_plan(engine, arguments.plan_id)
        elif arguments.command == "approve":
            plan = engine.state.get_plan(arguments.plan_id)
            display_plan(engine, plan.plan_id)
            expected = plan.fingerprint[-8:]
            print("\nReview the exact action above.")
            entered = input(f"Type approval code {expected} to approve, or press Enter to cancel: ").strip()
            if entered != expected:
                print("Cancelled. Nothing was approved.")
                return 2
            approved = engine.state.approve(plan.plan_id, broker.root, plan.fingerprint)
            print(f"Approved exact plan: {approved.plan_id}")
            print(f"Execute before: {approved.approved_expires_at}")
            print("Return to Hermes and ask it to apply the approved plan within 10 minutes.")
        elif arguments.command == "undo":
            confirmation = input(
                f"Type UNDO to reverse operation {arguments.operation_id}, or press Enter to cancel: "
            ).strip()
            if confirmation != "UNDO":
                print("Cancelled. Nothing was changed.")
                return 2
            print(json.dumps(engine.undo(arguments.operation_id), indent=2))
    except BrokerPolicyViolation as exc:
        print(f"Rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
