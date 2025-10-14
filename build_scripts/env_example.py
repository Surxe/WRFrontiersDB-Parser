#!/usr/bin/env python3
"""
Build script to generate .env.example from OPTIONS_SCHEMA

This script creates a new .env.example file based on the option schema,
ensuring documentation stays in sync with the actual option definitions.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Set

# Add src directory to path to import options module
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from options_schema import OPTIONS_SCHEMA


def generate_env_example() -> str:
    """Generate .env.example content from OPTIONS_SCHEMA."""
    
    # Header
    header = [
        "# Use forward slashes \"/\" in paths for compatibility across platforms",
    ]
    
    lines = header + [""]  # Add blank line after header
    
    def process_option(option_name: str, details: Dict[str, Any]) -> None:
        """Process a single option and add it to the lines."""
        env_var = details["env"]
        help_text = details.get("help", "")
        default = details.get("default", "")
        depends_on = details.get("depends_on", [])
        
        # Convert default value to string representation for .env file
        if default is None:
            default_str = ""
        elif isinstance(default, bool):
            default_str = "True" if default else "False"
        elif isinstance(default, Path):
            default_str = str(default) if default else ""
        else:
            default_str = str(default)
        
        # Add comment with help text
        if help_text:
            # Wrap long help text
            if len(help_text) > 80:
                # Simple word wrapping
                words = help_text.split()
                current_line = "# "
                for word in words:
                    if len(current_line + word) > 80:
                        lines.append(current_line.rstrip())
                        current_line = "# " + word + " "
                    else:
                        current_line += word + " "
                if current_line.strip() != "#":
                    lines.append(current_line.rstrip())
            else:
                lines.append(f"# {help_text}")
        
        # Add dependency information if present
        if depends_on:
            dep_str = " or ".join(depends_on)
            lines.append(f"# Required when {dep_str} is True")
        
        # Add the environment variable with default value
        lines.append(f'{env_var}="{default_str}"')
        lines.append("")  # Blank line after each option
    
    # Group options by section while preserving order
    sections_data = {}
    section_order = []
    
    for option_name, details in OPTIONS_SCHEMA.items():
        section = details.get("section", "Other")
        if section not in sections_data:
            sections_data[section] = []
            section_order.append(section)
        sections_data[section].append((option_name, details))
    
    # Process options by section
    for i, section in enumerate(section_order):
        # Add extra blank line between sections (except before first section)
        if i > 0:
            lines.append("")
        
        lines.append(f"# {section}")
        
        # Process all options in this section
        for option_name, details in sections_data[section]:
            process_option(option_name, details)
    
    return "\n".join(lines)


def update_env_example() -> bool:
    """Update the .env.example file with generated content."""
    repo_root = Path(__file__).parent.parent
    env_example_path = repo_root / ".env.example"
    
    try:
        # Generate new content
        new_content = generate_env_example()
        
        # Write to .env.example
        with open(env_example_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        print(f"Successfully updated {env_example_path}")
        print(f"Generated {len(new_content.splitlines())} lines")
        
        # Show summary of options
        option_count = len(OPTIONS_SCHEMA)
        
        # Count dependent options (options with depends_on field)
        dependent_count = sum(
            1 for details in OPTIONS_SCHEMA.values()
            if "depends_on" in details
        )
        
        print(f"Processed {option_count} options ({option_count - dependent_count} root + {dependent_count} dependent)")
        
    except Exception as e:
        print(f"Error updating .env.example: {e}")
        return False
    
    return True


def validate_generated_file() -> bool:
    """Validate that the generated .env.example file is properly formatted."""
    repo_root = Path(__file__).parent.parent
    env_example_path = repo_root / ".env.example"
    
    if not env_example_path.exists():
        print(f"Generated file {env_example_path} does not exist")
        return False
    
    try:
        with open(env_example_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Basic validation checks
        has_header = any("Use forward slashes" in line for line in lines[:5])
        has_env_vars = any("=" in line and not line.strip().startswith("#") for line in lines)
        
        if not has_header:
            print("Warning: Generated file missing expected header")
            return False
        
        if not has_env_vars:
            print("Warning: Generated file contains no environment variables")
            return False
        
        print(f"Generated file validation passed ({len(lines)} lines)")
        return True
        
    except Exception as e:
        print(f"Error validating generated file: {e}")
        return False


def main() -> None:
    """Main function to run the build process."""
    print("Building .env.example from OPTIONS_SCHEMA...")
    print()
    
    # Update the .env.example file
    if not update_env_example():
        sys.exit(1)
    
    # Validate the generated file
    if not validate_generated_file():
        sys.exit(1)
    
    print()
    print("Build completed successfully!")
    print()
    print("Next steps:")
    print("- Review the generated .env.example file")
    print("- Update any option descriptions if needed in OPTIONS_SCHEMA")
    print("- Run this script again after schema changes to keep documentation in sync")


if __name__ == "__main__":
    main()