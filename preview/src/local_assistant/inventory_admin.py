from __future__ import annotations

import argparse
from pathlib import Path

from .capability_broker import BrokerPolicyViolation
from .inventory_broker import InventoryRootStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Human-side inventory-root allowlist manager")
    parser.add_argument("--config", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    add = subparsers.add_parser("add")
    add.add_argument("root_id")
    add.add_argument("path", type=Path)
    remove = subparsers.add_parser("remove")
    remove.add_argument("root_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    store = InventoryRootStore(arguments.config)
    try:
        if arguments.command == "list":
            roots = store.load()
            if not roots:
                print("No real folders are approved for metadata inventory.")
            for root in roots:
                print(f"{root.root_id}  {root.path}  added={root.added_at}")
        elif arguments.command == "add":
            root_id = store.validate_root_id(arguments.root_id)
            path = store.validate_root_path(arguments.path)
            print("Metadata-only inventory permission requested:")
            print(f"  Root ID: {root_id}")
            print(f"  Folder:  {path}")
            print("  Visible metadata: relative names, types, extensions, sizes, timestamps")
            print("  File contents: not readable")
            print("  File changes: not permitted")
            expected = f"ADD {root_id}"
            entered = input(f"Type {expected} to allow this folder, or press Enter to cancel: ").strip()
            if entered != expected:
                print("Cancelled. No inventory permission was added.")
                return 2
            added = store.add(root_id, path)
            print(f"Added metadata-only inventory root: {added.root_id}  {added.path}")
            print("Run /reload-mcp in Hermes or restart Hermes before using the new root.")
        elif arguments.command == "remove":
            root_id = store.validate_root_id(arguments.root_id)
            roots = {item.root_id: item for item in store.load()}
            if root_id not in roots:
                raise BrokerPolicyViolation(f"Unknown inventory root: {root_id}")
            print(f"Remove metadata inventory access: {root_id}  {roots[root_id].path}")
            expected = f"REMOVE {root_id}"
            entered = input(f"Type {expected} to remove access, or press Enter to cancel: ").strip()
            if entered != expected:
                print("Cancelled. Inventory permission was unchanged.")
                return 2
            removed = store.remove(root_id)
            print(f"Removed inventory root: {removed.root_id}")
            print("Run /reload-mcp in Hermes or restart Hermes to unload the removed root.")
    except BrokerPolicyViolation as exc:
        print(f"Rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
