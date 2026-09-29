from __future__ import annotations

import argparse
import json
from pathlib import Path

from .broker_mcp import (
    default_audit_path,
    default_operator_permissions_path,
    default_operator_quarantine_path,
    default_operator_state_path,
)
from .capability_broker import BrokerPolicyViolation
from .operator_engine import OperatorStateStore, PermissionedOperator
from .permission_center import PermissionCenter, PermissionRootStore
from .protected_payload import PayloadProtectionError, default_payload_protector


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Human-side permission, approval, recovery, and undo for Cypher v0.8"
    )
    parser.add_argument(
        "--permissions", type=Path, default=default_operator_permissions_path()
    )
    parser.add_argument("--state", type=Path, default=default_operator_state_path())
    parser.add_argument("--audit", type=Path, default=default_audit_path())
    parser.add_argument(
        "--quarantine", type=Path, default=default_operator_quarantine_path()
    )
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("permissions-list")
    add = commands.add_parser("permissions-add")
    add.add_argument("root_id")
    add.add_argument("folder", type=Path)
    add.add_argument(
        "capabilities",
        help=(
            "Comma-separated capabilities: read_text,create_text,replace_text,copy,move,"
            "rename,mkdir,quarantine. metadata is always added."
        ),
    )
    remove = commands.add_parser("permissions-remove")
    remove.add_argument("root_id")

    commands.add_parser("plans-list")
    show = commands.add_parser("plan-show")
    show.add_argument("plan_id")
    approve = commands.add_parser("plan-approve")
    approve.add_argument("plan_id")
    status = commands.add_parser("operation-status")
    status.add_argument("operation_id")
    undo = commands.add_parser("operation-undo")
    undo.add_argument("operation_id")
    commands.add_parser("reconcile")
    return parser


def _build_operator(arguments: argparse.Namespace) -> PermissionedOperator:
    roots = PermissionRootStore(arguments.permissions).load()
    permissions = PermissionCenter(roots, arguments.audit)
    state = OperatorStateStore(arguments.state, default_payload_protector())
    return PermissionedOperator(permissions, state, arguments.quarantine)


def _display_plan(operator: PermissionedOperator, plan_id: str) -> None:
    print(json.dumps(operator.human_review_plan(plan_id), indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    store = PermissionRootStore(arguments.permissions)
    try:
        if arguments.command == "permissions-list":
            records = store.load()
            if not records:
                print("No real-folder permissions are configured.")
            for record in records:
                print(
                    f"{record.root_id}  {record.path}  "
                    f"capabilities={','.join(sorted(record.capabilities))}"
                )
            return 0
        if arguments.command == "permissions-add":
            capabilities = [
                value.strip()
                for value in arguments.capabilities.split(",")
                if value.strip()
            ]
            print("Real-folder permission request:")
            print(f"  Root ID: {arguments.root_id}")
            print(f"  Folder:  {arguments.folder.expanduser().resolve(strict=True)}")
            print(f"  Capabilities: {', '.join(sorted(set(capabilities)))}")
            print("  No shell, administrator, permanent-delete, or network authority is included.")
            expected = f"ADD {arguments.root_id}"
            entered = input(f"Type {expected} to add this permission, or press Enter to cancel: ").strip()
            if entered != expected:
                print("Cancelled. Permissions were unchanged.")
                return 2
            record = store.add(arguments.root_id, arguments.folder, capabilities)
            print(f"Added permission root '{record.root_id}': {record.path}")
            print("Restart Hermes or run /reload-mcp before using this permission.")
            return 0
        if arguments.command == "permissions-remove":
            expected = f"REMOVE {arguments.root_id}"
            entered = input(
                f"Type {expected} to revoke this root, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. Permissions were unchanged.")
                return 2
            record = store.remove(arguments.root_id)
            print(f"Removed permission root '{record.root_id}': {record.path}")
            print("Restart Hermes or run /reload-mcp to unload it from the broker.")
            return 0

        operator = _build_operator(arguments)
        if arguments.command == "plans-list":
            plans = operator.state.list_plans()
            if not plans:
                print("No permissioned-operator plans are stored.")
            for plan in plans:
                print(
                    f"{plan.plan_id}  {plan.status:21}  items={len(plan.actions):2}  "
                    f"code={plan.fingerprint[-8:]}"
                )
        elif arguments.command == "plan-show":
            _display_plan(operator, arguments.plan_id)
        elif arguments.command == "plan-approve":
            plan = operator.state.get_plan(arguments.plan_id)
            _display_plan(operator, plan.plan_id)
            expected = plan.fingerprint[-8:]
            print("\nReview every exact source, destination, action, byte count, and content preview above.")
            entered = input(
                f"Type approval code {expected} to approve, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. Nothing was approved.")
                return 2
            approved = operator.state.approve(plan.plan_id, plan.fingerprint)
            print(f"Approved exact operator plan: {approved.plan_id}")
            print(f"Execute before: {approved.approved_expires_at}")
            print("Return to Cypher and ask it to apply the approved plan within 10 minutes.")
        elif arguments.command == "operation-status":
            print(
                json.dumps(
                    operator.operation_status(arguments.operation_id),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif arguments.command == "operation-undo":
            expected = f"UNDO {arguments.operation_id}"
            entered = input(
                f"Type {expected} to reverse this operation, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. No file was changed.")
                return 2
            print(
                json.dumps(
                    operator.undo_operation(arguments.operation_id),
                    indent=2,
                    ensure_ascii=False,
                )
            )
        elif arguments.command == "reconcile":
            result = operator.reconcile_incomplete()
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["safe_to_start"] else 1
    except (BrokerPolicyViolation, PayloadProtectionError, OSError) as exc:
        print(f"Rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
