#!/usr/bin/env python3
"""
Build script to generate README option documentation from OPTIONS_SCHEMA

This script creates markdown documentation for all options that can be
included in the README.md file, ensuring documentation stays in sync.
"""

import os
import sys
from pathlib import Path

# Add src directory to path to import options module
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from options import OPTIONS_SCHEMA


def generate_by_process_section():
    """Generate option documentation organized by sections from OPTIONS_SCHEMA."""
    
    lines = []
    
    # Group options by section
    sections_data = {}
    for option_name, details in OPTIONS_SCHEMA.items():
        section = details.get("section", "Other")
        if section not in sections_data:
            sections_data[section] = []
        sections_data[section].append((option_name, details, False))
        
        # Add section_options
        if "section_options" in details:
            for sub_option, sub_details in details["section_options"].items():
                sections_data[section].append((sub_option, sub_details, True))
    
    # Generate documentation for each section
    for section, options in sections_data.items():
        lines.extend([
            f"#### {section}",
            "",
        ])
        for option_name, details, is_section_option in options:
            add_option_doc_to_lines(lines, option_name, details, is_section_option)
        lines.append("")
    
    return "\n".join(lines)



def add_option_doc_to_lines(lines, option_name, details, is_section_option=False, indent_level=0):
    """Add documentation for a single option to the lines list."""
    env_var = details["env"]
    help_text = details.get("help", "")
    default = details.get("default", "")
    arg_name = details["arg"]
    
    # Convert default value to readable string
    if default is None:
        default_str = "None - required if section enabled"
    elif isinstance(default, bool):
        default_str = f'`"{str(default).lower()}"`'
    elif isinstance(default, str):
        if default == "":
            default_str = '`""` (empty for latest)' if 'manifest' in option_name.lower() else '`""`'
        else:
            default_str = f'`"{default}"`'
    else:
        default_str = f'`"{default}"`'
    
    # Create the option entry
    indent = "  " * indent_level if is_section_option else ""
    bullet = "-" if not is_section_option else "*"
    
    lines.append(f"{indent}{bullet} **{env_var}** - {help_text}")
    lines.append(f"{indent}  - Default: {default_str}")
    lines.append(f"{indent}  - Command line: `{arg_name}`")
    
    # Add links if present
    if "links" in details:
        for link_name, link_url in details["links"].items():
            lines.append(f"{indent}  - See [{link_name}]({link_url}) for available values")
    
    # Add extended help if present
    if "help_extended" in details:
        lines.append(f"{indent}  - {details['help_extended']}")
    
    lines.append("")  # Blank line after each option


def generate_full_option_section():
    """Generate the complete option documentation section."""
    
    lines = []
    
    # Add process-organized documentation
    lines.append(generate_by_process_section())
    
    return "\n".join(lines)


def write_option_docs():
    """Write option documentation to files."""
    build_dir = Path(__file__).parent.parent / ".temp"
    os.makedirs(build_dir, exist_ok=True)
    
    # Generate different formats
    full_section = generate_full_option_section()
    env_vars_only = generate_by_process_section()
    
    # Write full section
    full_path = build_dir / "readme_options_section.md"
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(full_section)
    
    return full_path


def validate_generated_docs():
    """Validate that the generated documentation looks correct."""
    build_dir = Path(__file__).parent.parent / ".temp"
    
    files_to_check = [
        "readme_options_section.md"
    ]
    
    for filename in files_to_check:
        filepath = build_dir / filename
        
        if not filepath.exists():
            print(f"Generated file {filepath} does not exist")
            return False
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Basic validation checks
            if len(content) < 100:
                print(f"Warning: Generated file {filename} seems too short")
                return False
            
            # Check for expected content
            if filename == "readme_options_section.md":
                if "#### Logging" not in content:
                    print(f"Warning: {filename} missing expected sections")
                    return False
            
            print(f"Generated {filename} ({len(content.splitlines())} lines)")
            
        except Exception as e:
            print(f"Error validating {filename}: {e}")
            return False
    
    return True

def main():
    """Main function to run the option documentation build."""
    
    print("Building README option documentation from OPTIONS_SCHEMA...")
    print()
    
    try:
        # Generate documentation files
        full_path = write_option_docs()
        
        # Validate generated files
        if not validate_generated_docs():
            print("Validation failed")
            sys.exit(1)
        
        print("\nGenerated Files:")
        print(f"   {full_path.name} - Complete option section")
        
        print("\nOption documentation build completed successfully!")
        
    except Exception as e:
        print(f"Error building option documentation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()