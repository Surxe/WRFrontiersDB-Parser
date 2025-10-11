#!/usr/bin/env python3
"""
Master build script to update all generated documentation files (Windows compatible)

This script:
1. Generates .env.example from OPTIONS_SCHEMA
2. Generates README option documentation  
3. Updates README.md with the generated content

Usage:
    python build/build_docs_simple.py
"""

import subprocess
import sys
from pathlib import Path

def run_script(script_name: str) -> bool:
    """Run a build script and check for success."""
    
    build_dir = Path(__file__).parent
    script_path = build_dir / script_name
    
    if not script_path.exists():
        print(f"ERROR: Script {script_name} not found at {script_path}")
        return False
    
    try:
        print(f"Running {script_name}...")
        result = subprocess.run([sys.executable, str(script_path)], 
                              capture_output=True, text=True, check=True)
        print(f"SUCCESS: {script_name} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"ERROR: {script_name} failed:")
        if e.stdout:
            print(f"   stdout: {e.stdout}")
        if e.stderr:
            print(f"   stderr: {e.stderr}")
        return False

def main() -> bool:
    """Run all documentation build scripts."""
    
    print("Building all documentation from OPTIONS_SCHEMA...")
    print("=" * 60)
    
    # First, let's just run the update script since we already have the generated files
    scripts_to_run = [
        "readme_options.py",  # Generate option docs
        "update_readme.py",     # Update README.md with generated content
        "env_example.py"    # Generate .env.example
    ]
    
    success_count = 0
    for script in scripts_to_run:
        if run_script(script):
            success_count += 1
        print()
    
    # Summary
    total_scripts = len(scripts_to_run)
    print("=" * 60)
    if success_count == total_scripts:
        print(f"SUCCESS: All {total_scripts} build scripts completed!")
        print("\nGenerated/Updated Files:")
        print("   .env.example - Environment configuration template")
        print("   README.md - Updated with current option documentation")
        return True
    else:
        print(f"ERROR: {total_scripts - success_count} of {total_scripts} scripts failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)