from __future__ import annotations

from pathlib import Path
import sys

from .audit import AuditStore
from .config import Settings
from .file_organizer import GraphicOrganizer
from .local_model import LocalModel, LocalModelUnavailable
from .policy import PolicyEngine, PolicyViolation


GRAPHIC_EXECUTION_COMMAND = "/organize-graphics"


def is_graphic_execution_command(value: str) -> bool:
    """Return True only for the explicit file-tool command.

    Natural-language requests always go to the model. This prevents words in a
    question (including negated requests such as "do not scan") from activating
    a computer action.
    """
    return value.strip().lower() == GRAPHIC_EXECUTION_COMMAND


def print_plan(plan) -> None:
    print(f"\nPlan: {plan.plan_id}")
    print(f"Files proposed: {len(plan.items)}\n")
    for index, item in enumerate(plan.items, 1):
        print(f"{index:>4}. [{item.category}] {item.source}")
        print(f"      -> {item.destination}")
        print(f"      {item.reason}")
    print(f"\nApproval fingerprint: {plan.fingerprint}")


def parse_selection(value: str, maximum: int) -> list[int]:
    normalized = value.strip().upper()
    if normalized == "ALL":
        return list(range(maximum))
    chosen: set[int] = set()
    for part in normalized.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start_text, end_text = part.split("-", maxsplit=1)
            start, end = int(start_text), int(end_text)
            if start > end:
                raise ValueError("Selection range is reversed")
            values = range(start, end + 1)
        else:
            values = (int(part),)
        for number in values:
            if number < 1 or number > maximum:
                raise ValueError(f"Selection {number} is outside 1-{maximum}")
            chosen.add(number - 1)
    return sorted(chosen)


def run_graphic_task(organizer: GraphicOrganizer, stop_file: Path) -> None:
    print("Scanning approved user folders locally. No files are being moved...")
    candidates = organizer.scan()
    if not candidates:
        print("No graphic candidates found.")
        return
    plan = organizer.make_plan(candidates)
    print_plan(plan)
    answer = input(
        "\nChoose files to move (example: 1,3,7-10 or ALL). Press Enter to cancel: "
    ).strip()
    if not answer:
        print("Cancelled. No files were changed.")
        return
    selection = parse_selection(answer, len(plan.items))
    if not selection:
        print("Cancelled. No files were changed.")
        return
    approved_candidates = [candidates[index] for index in selection]
    approved_plan = organizer.make_plan(approved_candidates)
    print_plan(approved_plan)
    confirmation = input("\nType MOVE to execute exactly this approved plan: ").strip()
    if confirmation != "MOVE":
        print("Cancelled. No files were changed.")
        return
    operation_id = organizer.execute(approved_plan, approved_plan.fingerprint, stop_file)
    print(f"Completed operation {operation_id}. Use 'undo {operation_id}' to restore the files.")


def main() -> None:
    settings = Settings.default()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    stop_file = settings.data_dir / "STOP"
    audit = AuditStore(settings.data_dir)
    policy = PolicyEngine(settings)
    organizer = GraphicOrganizer(settings, policy, audit)
    model = LocalModel()

    print("Local Agent 0.1.1 — all reasoning and execution are local")
    print("Type 'help' for commands. No administrator access is requested.")
    while True:
        try:
            command = input("\nYou> ").strip()
            normalized = command.lower()
            if normalized in {"exit", "quit"}:
                return
            if normalized == "help":
                print(
                    "Commands: /organize-graphics | status | stop | resume | "
                    "undo <operation-id> | quit"
                )
            elif normalized == "status":
                state = "STOPPED" if stop_file.exists() else "READY"
                print(f"Assistant: {state}; data: {settings.data_dir}; destination: {settings.destination}")
            elif normalized == "stop":
                stop_file.touch(exist_ok=True)
                print("Emergency stop enabled. New actions are blocked.")
            elif normalized == "resume":
                stop_file.unlink(missing_ok=True)
                print("Emergency stop cleared.")
            elif normalized.startswith("undo "):
                count = organizer.undo(command.split(maxsplit=1)[1])
                print(f"Restored {count} file(s).")
            elif is_graphic_execution_command(command):
                run_graphic_task(organizer, stop_file)
            else:
                try:
                    print(f"Assistant> {model.chat(command)}")
                except LocalModelUnavailable:
                    print("Ollama is not reachable on localhost. Start Ollama, or try 'help'.")
        except (KeyboardInterrupt, EOFError):
            print("\nStopped.")
            return
        except PolicyViolation as error:
            print(f"Blocked by security policy: {error}")
        except Exception as error:
            print(f"Action failed safely: {error}", file=sys.stderr)
