# How module scalars are linked to their character module, and ability scalars are linked to theri abilities

# Module.json
* character_module_mounts: `list[dict]`
  * character_module_id: `str` - Links to `CharacterModule.id`
* module_scalars: `dict`
  * levels
    * constants
    * variables
  * default_scalars
  * module_name: `str` - May link to `CharacterModule.module_scalar.module_name`
* abilities_scalars: `list[dict]`
  * `<index>`: `int` - Links to `CharacterModule.abilities_ids.__index__`
  * `<element>`: `dict`
    * primary_stat_id
    * secondary_stat_id
    * levels
    * default_scalars

# CharacterModule.json
* id: `str`
* module_scalar
  * module_name
  * default_scalars
* abilities_ids: list
  * `<index>`: `int`
  * `<element>`: `str` - Links to `Ability.id`

# Ability.json
* id