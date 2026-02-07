# Standards

## Code Conventions

### Case
- **snake_case** - Used for variables and functions
- **PascalCase** - Used for class names (e.g., `Options`, `ParseObject`)
- ***CREAMING_SNAKE_CASE** - Used for schema keys and environment variables (e.g., `LOG_LEVEL`, `SHOULD_PARSE`)

### Path Variable Naming
* **Folder Path** → `dir` (e.g., `output_dir`, `export_dir`)
* **File Path**
  * **Executable File Path** → `cmd` (e.g., none currently)
  * **Other File Path** → `file` (e.g., `log_file`, `asset_file`, `version_file`)
* **Path** - Generic - Old convention, ideally is changed to either dir, cmd, or file

### Function/Method Naming
#### Methods
* **Private methods** - Methods that use (not just have) `self` arg and are not intended to be used externally. Prefixed with `_` (e.g., `_process_schema`)
* **Public methods** - Methods that use (not just have) `self` arg and are intended to be used externally. Not prefixed with `_`

#### Variables
* Data is an id - `currency_id` - (e.g. `DA_Module_AmmoFabricator.0`)
* Data is a list of ids - `currencies_ids` - (e.g. `['DA_Module_AmmoFabricator.0']`)
* Data is a ref - `currency_ref` - (e.g. `OBJID_Currency::DA_Module_AmmoFabricator.0`)
* Data is a list of refs - `currencies_refs` - (e.g. `['OBJID_Currency::DA_Module_AmmoFabricator.0']`)
* Data is a dictionary that contains refs - `character_module_mounts` -
```python
character_module_mounts = {
    'mount': 'Left',
    'character_module_ref': 'OBJID_CharacterModule::DA_Module_AmmoFabricator.0',
}
```

  
## File & Directory Structure

### Case
* **Documentation files** - ALLCAPSNOSPACE (e.g., `README.md`, `STANDARDS.md`)
* **Other directories/files** - snake_case (e.g., `parsers/`, `build_scripts/`, `parse.py`)

### Patterns

## Terminology

### Settings / Options
* **Argument** - CLI provided variable at runtime, i.e. `--log-level`
* **Parameter / Environment Variable** - `.env` provided variable, i.e. `LOG_LEVEL`
* **Default** - Default value for a given option
* **Option** - Argument, parameter, or default (in descending order of priority)
* **Root Option** - An option that has sub-options via `section_options` (e.g., `SHOULD_PARSE`)
* **Section Option** - A sub-option of the section's root option (e.g., `OUTPUT_DIR` under `SHOULD_PARSE`)

### Logging Standards
* **Log Levels** - `TRACE`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
* **Sensitive Data** - Password fields masked with `***HIDDEN***`

## Testing Conventions

### Test File Structure
* **Test files** - `test_{module_name}.py`
* **Test classes** - `Test{ClassName}` (e.g., `TestOptions`)
* **Test methods** - `test_{functionality}_{scenario}` (e.g., `test_nested_dict_all_levels`)

### Test Organization
* **setUp/tearDown** - Use for test preparation and cleanup
* **Mock objects** - Prefix with `mock_` (e.g., `mock_logger`, `mock_subprocess`)
* **Temporary directories** - Create in `setUp`, clean in `tearDown`
* **Assertions** - Use descriptive assertion methods