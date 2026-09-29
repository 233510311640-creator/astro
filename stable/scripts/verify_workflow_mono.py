"""Developer-only workflow behavioral check under an existing Mono runtime.

Usage: python3 -B scripts/verify_workflow_mono.py --mono-root /path/to/extracted/runtime
The runtime root must contain usr/bin/mono-sgen and usr/lib/mono/4.5/mcs.exe.
No downloads, system installation, app actions, or resident-host changes occur.
This supplements, and does not replace, the native Windows installer self-test.
"""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mono-root", type=Path, required=True)
    args = parser.parse_args()
    runtime = args.mono_root.resolve()
    mono = runtime / "usr/bin/mono-sgen"
    compiler = runtime / "usr/lib/mono/4.5/mcs.exe"
    if not mono.is_file() or not compiler.is_file():
        parser.error("The supplied root must contain an existing Mono runtime and compiler")
    source = Path(__file__).resolve().parents[1] / "windows/Cypher.CorePreview"
    env = os.environ.copy()
    env["MONO_PATH"] = str(compiler.parent)
    env["MONO_CFG_DIR"] = str(runtime / "etc")
    with tempfile.TemporaryDirectory(prefix="cypher-workflow-csharp-") as folder:
        directory = Path(folder)
        runner = directory / "Main.cs"
        runner.write_text(
            "class MainClass { static int Main() { return Cypher.CorePreview.WindowsWorkflowSelfTest.Run(); } }",
            encoding="utf-8",
        )
        exe = directory / "WorkflowTests.exe"
        subprocess.run([
            str(mono), str(compiler), "-nologo", "-target:exe", "-codepage:65001", f"-out:{exe}",
            "-r:System.dll", "-r:System.Core.dll", "-r:System.Web.Extensions.dll",
            str(source / "WindowsWorkflow.cs"), str(source / "WindowsWorkflowSelfTest.cs"), str(runner),
        ], env=env, check=True, timeout=60)
        result = subprocess.run([str(mono), str(exe)], env=env, check=False, timeout=60)
        if result.returncode:
            raise SystemExit(f"Workflow behavioral self-test failed at case {result.returncode}")
    print("PASS: actual C# workflow self-test cases 100 through 147 under Mono; WPF was not run.")


if __name__ == "__main__":
    main()
