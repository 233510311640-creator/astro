from __future__ import annotations

import argparse
import json
from pathlib import Path

from .capability_broker import BrokerPolicyViolation
from .inventory_broker import InventoryRootStore, MetadataInventoryBroker
from .organization_planner import DryRunOrganizationPlanner, OrganizationPlanStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Human-side dry-run organization destination and plan manager"
    )
    parser.add_argument("--inventory-config", type=Path, required=True)
    parser.add_argument("--destination-config", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("destinations")
    add = subparsers.add_parser("add-destination")
    add.add_argument("root_id")
    add.add_argument("path", type=Path)
    remove = subparsers.add_parser("remove-destination")
    remove.add_argument("root_id")
    subparsers.add_parser("plans")
    for command in ("show", "review", "reject"):
        child = subparsers.add_parser(command)
        child.add_argument("plan_id")
    return parser


def _planner(arguments: argparse.Namespace) -> DryRunOrganizationPlanner:
    source_roots = InventoryRootStore(arguments.inventory_config).load()
    destinations = InventoryRootStore(arguments.destination_config).load()
    inventory = MetadataInventoryBroker(source_roots, arguments.audit)
    state = OrganizationPlanStore(arguments.state)
    return DryRunOrganizationPlanner(inventory, destinations, state, arguments.audit)


def _print_json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=True, indent=2))


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    destination_store = InventoryRootStore(arguments.destination_config)
    try:
        if arguments.command == "destinations":
            roots = destination_store.load()
            if not roots:
                print("No organization planning destinations are approved.")
            for root in roots:
                print(f"{root.root_id}  {root.path}  added={root.added_at}")
        elif arguments.command == "add-destination":
            root_id = destination_store.validate_root_id(arguments.root_id)
            path = destination_store.validate_root_path(arguments.path)
            print("Dry-run organization destination requested:")
            print(f"  Destination ID: {root_id}")
            print(f"  Folder:         {path}")
            print("  v0.5 permission: propose paths under this folder only")
            print("  File contents:   not readable")
            print("  File changes:    impossible in this release")
            expected = f"ADD-DESTINATION {root_id}"
            entered = input(
                f"Type {expected} to allow planning, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. No planning destination was added.")
                return 2
            added = destination_store.add(root_id, path)
            print(
                f"Added dry-run planning destination: {added.root_id}  {added.path}"
            )
            print("Run /reload-mcp in Hermes or restart Hermes before using it.")
        elif arguments.command == "remove-destination":
            root_id = destination_store.validate_root_id(arguments.root_id)
            roots = {item.root_id: item for item in destination_store.load()}
            if root_id not in roots:
                raise BrokerPolicyViolation(
                    f"Unknown organization destination: {root_id}"
                )
            print(
                f"Remove organization planning destination: {root_id}  {roots[root_id].path}"
            )
            expected = f"REMOVE-DESTINATION {root_id}"
            entered = input(
                f"Type {expected} to remove it, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. Planning permissions were unchanged.")
                return 2
            destination_store.remove(root_id)
            print(f"Removed organization planning destination: {root_id}")
            print("Run /reload-mcp in Hermes or restart Hermes to unload it.")
        elif arguments.command == "plans":
            plans = OrganizationPlanStore(arguments.state).list()
            if not plans:
                print("No dry-run organization plans exist.")
            for plan in plans:
                print(
                    f"{plan.plan_id}  {plan.status}  items={len(plan.items)}  "
                    f"source={plan.source_root_id}  destination={plan.destination_root_id}  "
                    f"expires={plan.expires_at}"
                )
        elif arguments.command == "show":
            planner = _planner(arguments)
            _print_json(planner.get_plan(arguments.plan_id))
            _print_json(planner.validate_plan(arguments.plan_id))
        elif arguments.command == "review":
            planner = _planner(arguments)
            plan = planner.state.get(arguments.plan_id)
            public = planner.public_plan(plan)
            validation = planner.validate_plan(plan.plan_id)
            _print_json(public)
            _print_json(validation)
            if not validation["ready_for_human_review"]:
                raise BrokerPolicyViolation(
                    "Plan is not ready for review; create a fresh valid proposal"
                )
            expected = f"REVIEW {plan.fingerprint[-8:]}"
            entered = input(
                f"Type {expected} to record review, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. Plan was not marked reviewed.")
                return 2
            reviewed = planner.state.mark_reviewed(plan.plan_id, plan.fingerprint)
            print(f"Reviewed dry-run plan: {reviewed.plan_id}")
            print("No execution permission was granted. v0.5 cannot move files.")
        elif arguments.command == "reject":
            planner = _planner(arguments)
            plan = planner.state.get(arguments.plan_id)
            _print_json(planner.public_plan(plan))
            expected = f"REJECT {plan.fingerprint[-8:]}"
            entered = input(
                f"Type {expected} to reject this plan, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. Plan status was unchanged.")
                return 2
            rejected = planner.state.mark_rejected(plan.plan_id, plan.fingerprint)
            print(f"Rejected dry-run plan: {rejected.plan_id}")
            print("No real files were changed.")
    except (BrokerPolicyViolation, OSError) as exc:
        print(f"Rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
