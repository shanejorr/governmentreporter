#!/usr/bin/env python3
"""
Automated script to run all example output files and save their JSON results.

This script executes all the example files in the example_output directory
and saves their JSON output to individual files in the same directory.

Usage:
    python example_output/run_all_examples.py

    # Or from the example_output directory:
    cd example_output && python run_all_examples.py

The script will create JSON files with the naming pattern:
    [module]_[filename]_output.json

For example:
    - apis_base_output.json
    - utils_citations_output.json
    - processors_chunking_output.json
    etc.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def get_script_directory() -> Path:
    """Get the directory where this script is located."""
    return Path(__file__).parent.absolute()


def find_example_scripts() -> List[Tuple[str, Path, bool]]:
    """
    Find all Python example scripts in the example_output directory structure.

    Returns:
        List of tuples containing (module_name, script_path, needs_uv_run)
    """
    script_dir = get_script_directory()
    scripts = []

    # Scripts that need uv run (require virtual environment dependencies)
    uv_run_scripts = {
        "database/qdrant_client.py",
        "apis/court_listener.py",
        "apis/federal_register.py",
        "processors/llm_extraction.py",
    }

    # Find all Python files except this script itself
    for py_file in script_dir.rglob("*.py"):
        if py_file.name == "run_all_examples.py":
            continue

        # Get relative path from script_dir
        rel_path = py_file.relative_to(script_dir)

        # Create module name from path (e.g., "apis/base.py" -> "apis_base")
        module_name = str(rel_path).replace("/", "_").replace(".py", "")

        # Check if this script needs uv run
        needs_uv = str(rel_path) in uv_run_scripts

        scripts.append((module_name, py_file, needs_uv))

    return sorted(scripts)


def run_script(script_path: Path, needs_uv: bool) -> Tuple[bool, str, str]:
    """
    Run a single example script and capture its output.

    Args:
        script_path: Path to the Python script
        needs_uv: Whether the script needs to be run with 'uv run'

    Returns:
        Tuple of (success, stdout, stderr)
    """
    try:
        # Special handling for qdrant_client.py to avoid circular import
        temp_script_path = None
        if script_path.name == "qdrant_client.py":
            # Create a temporary copy with different name
            temp_script_path = script_path.parent / "temp_qdrant_example.py"
            import shutil

            shutil.copy2(script_path, temp_script_path)
            actual_script_path = temp_script_path
        else:
            actual_script_path = script_path

        if needs_uv:
            cmd = ["uv", "run", "python", str(actual_script_path)]
        else:
            cmd = ["python", str(actual_script_path)]

        # Change to the project root directory for consistent imports
        project_root = (
            script_path.parent.parent
        )  # Go up from example_output to project root

        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,  # 60 second timeout per script
        )

        # Clean up temporary file if created
        if temp_script_path and temp_script_path.exists():
            temp_script_path.unlink()

        return result.returncode == 0, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        # Clean up temporary file if created
        if temp_script_path and temp_script_path.exists():
            temp_script_path.unlink()
        return False, "", "Script timed out after 60 seconds"
    except Exception as e:
        # Clean up temporary file if created
        if temp_script_path and temp_script_path.exists():
            temp_script_path.unlink()
        return False, "", f"Error running script: {str(e)}"


def save_json_output(module_name: str, output: str, script_dir: Path) -> bool:
    """
    Save the JSON output to a file.

    Args:
        module_name: Name for the output file
        output: JSON output string
        script_dir: Directory to save the file in

    Returns:
        True if successful, False otherwise
    """
    try:
        output_file = script_dir / f"{module_name}_output.json"

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)

        return True

    except Exception as e:
        print(f"  ❌ Error saving output: {str(e)}")
        return False


def main():
    """Main function to run all example scripts and save outputs."""
    print("🚀 Running all example output scripts...")
    print("=" * 60)

    script_dir = get_script_directory()
    scripts = find_example_scripts()

    if not scripts:
        print("❌ No example scripts found!")
        return 1

    print(f"Found {len(scripts)} example scripts to run:")
    for module_name, script_path, needs_uv in scripts:
        uv_indicator = " (uv run)" if needs_uv else ""
        print(f"  • {module_name}{uv_indicator}")

    print("\n" + "=" * 60)
    print("Running scripts and saving outputs...\n")

    results: Dict[str, bool] = {}

    for module_name, script_path, needs_uv in scripts:
        print(f"📄 Running {module_name}...")

        # Run the script
        success, stdout, stderr = run_script(script_path, needs_uv)

        if success and stdout.strip():
            # Save the JSON output
            if save_json_output(module_name, stdout, script_dir):
                print(f"  ✅ Saved to {module_name}_output.json")
                results[module_name] = True
            else:
                results[module_name] = False
        elif success and not stdout.strip():
            print(f"  ⚠️  Script ran but produced no output")
            results[module_name] = False
        else:
            print(f"  ❌ Script failed")
            if stderr:
                # Print first few lines of error for debugging
                error_lines = stderr.strip().split("\n")
                print(
                    f"     Error: {error_lines[-1]}"
                )  # Show last line (usually the actual error)
            results[module_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary:")

    successful = sum(1 for success in results.values() if success)
    total = len(results)

    print(f"✅ Successfully generated: {successful}/{total} JSON files")

    if successful > 0:
        print(f"\n📁 JSON files saved in: {script_dir}")
        print("   Files created:")
        for module_name, success in results.items():
            if success:
                print(f"     • {module_name}_output.json")

    if successful < total:
        print(f"\n❌ Failed scripts:")
        for module_name, success in results.items():
            if not success:
                print(f"     • {module_name}")
        print(
            "\n💡 Tip: Failed scripts may need environment variables or dependencies."
        )
        print("   Check the individual script outputs for details.")

    return 0 if successful == total else 1


if __name__ == "__main__":
    sys.exit(main())
