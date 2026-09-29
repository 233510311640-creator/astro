from __future__ import annotations

import argparse
from pathlib import Path

from .broker_mcp import default_windows_apps_path
from .capability_broker import BrokerPolicyViolation
from .windows_operator import WindowsAppStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Human-side allowlist manager for Cypher Windows applications"
    )
    parser.add_argument("--config", type=Path, default=default_windows_apps_path())
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    commands.add_parser("seed-builtins")
    add = commands.add_parser("add")
    add.add_argument("app_id")
    add.add_argument("display_name")
    add.add_argument("executable", type=Path)
    add.add_argument("--app-user-model-id")
    add.add_argument("--allow-text-entry", action="store_true")
    remove = commands.add_parser("remove")
    remove.add_argument("app_id")
    text_entry = commands.add_parser("set-text-entry")
    text_entry.add_argument("app_id")
    text_entry.add_argument("state", choices=("on", "off"))
    app_identity = commands.add_parser("set-app-user-model-id")
    app_identity.add_argument("app_id")
    app_identity.add_argument("app_user_model_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    store = WindowsAppStore(arguments.config)
    try:
        if arguments.command == "list":
            records = store.load()
            if not records:
                print("No Windows applications are registered.")
            for record in records:
                identity = record.app_user_model_id or "none"
                text_entry = "enabled" if record.allow_text_entry else "disabled"
                print(
                    f"{record.app_id}  {record.display_name}  {record.executable}  "
                    f"AUMID={identity}  text-entry={text_entry}"
                )
            return 0
        if arguments.command == "seed-builtins":
            result = store.seed_builtin_apps()
            added = ", ".join(result["added"]) or "none"
            upgraded = ", ".join(result["upgraded"]) or "none"
            unavailable = ", ".join(result["unavailable"]) or "none"
            print(f"Built-in Windows apps added: {added}")
            print(f"Built-in Windows apps upgraded: {upgraded}")
            print(f"Built-in Windows apps unavailable: {unavailable}")
            print(f"Registered Windows apps: {result['registered']}")
            return 0
        if arguments.command == "add":
            app_id = store.validate_app_id(arguments.app_id)
            display_name = store.validate_display_name(arguments.display_name)
            executable = store.validate_executable(arguments.executable)
            app_user_model_id = store.validate_app_user_model_id(
                arguments.app_user_model_id
            )
            print("Windows application launch permission requested:")
            print(f"  App ID:       {app_id}")
            print(f"  Display name: {display_name}")
            print(f"  Executable:   {executable}")
            print(f"  AppUserModelID: {app_user_model_id or 'none'}")
            print(
                "  Text entry:   "
                + ("enabled" if arguments.allow_text_entry else "disabled")
            )
            print("  Arguments:    none (Cypher cannot supply command-line arguments)")
            expected = f"ADD APP {app_id}"
            entered = input(
                f"Type {expected} to register this app, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. The Windows app allowlist was unchanged.")
                return 2
            record = store.add(
                app_id,
                display_name,
                executable,
                app_user_model_id=app_user_model_id,
                allow_text_entry=arguments.allow_text_entry,
            )
            print(f"Registered Windows app '{record.app_id}': {record.executable}")
            print("Restart Hermes or run /reload-mcp before using the new app.")
            return 0
        if arguments.command == "remove":
            app_id = store.validate_app_id(arguments.app_id)
            records = {record.app_id: record for record in store.load()}
            if app_id not in records:
                raise BrokerPolicyViolation(f"Unknown Windows app: {app_id}")
            print(f"Remove Windows app access: {app_id}  {records[app_id].executable}")
            expected = f"REMOVE APP {app_id}"
            entered = input(
                f"Type {expected} to remove access, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. The Windows app allowlist was unchanged.")
                return 2
            removed = store.remove(app_id)
            print(f"Removed Windows app: {removed.app_id}")
            print("Restart Hermes or run /reload-mcp to unload the removed app.")
            return 0
        if arguments.command == "set-text-entry":
            app_id = store.validate_app_id(arguments.app_id)
            enabled = arguments.state == "on"
            records = {record.app_id: record for record in store.load()}
            if app_id not in records:
                raise BrokerPolicyViolation(f"Unknown Windows app: {app_id}")
            expected = f"SET TEXT ENTRY {app_id} {arguments.state.upper()}"
            entered = input(
                f"Type {expected} to change this capability, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. The Windows app allowlist was unchanged.")
                return 2
            record = store.set_text_entry(app_id, enabled)
            print(
                f"Text entry for '{record.app_id}' is now "
                + ("enabled." if record.allow_text_entry else "disabled.")
            )
            print("Restart Cypher before using the changed capability.")
            return 0
        if arguments.command == "set-app-user-model-id":
            app_id = store.validate_app_id(arguments.app_id)
            value = (
                None
                if arguments.app_user_model_id.casefold() == "none"
                else store.validate_app_user_model_id(arguments.app_user_model_id)
            )
            records = {record.app_id: record for record in store.load()}
            if app_id not in records:
                raise BrokerPolicyViolation(f"Unknown Windows app: {app_id}")
            expected = f"SET AUMID {app_id}"
            entered = input(
                f"Type {expected} to change the packaged-app identity, or press Enter to cancel: "
            ).strip()
            if entered != expected:
                print("Cancelled. The Windows app allowlist was unchanged.")
                return 2
            record = store.set_app_user_model_id(app_id, value)
            print(
                f"AppUserModelID for '{record.app_id}' is now "
                f"{record.app_user_model_id or 'none'}."
            )
            print("Restart Cypher before using the changed identity.")
            return 0
    except (BrokerPolicyViolation, OSError) as exc:
        print(f"Rejected: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
