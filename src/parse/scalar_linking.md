# How module scalars are linked to their character module, and ability scalars are linked to theri abilities

# Module.json
* character_module_mounts: `list[dict]` (is technically a list but only ever has one element for ability scalar purposes)
  * character_module_ref: `str` - Links to `CharacterModule.id`
* module_scalars: `dict`
  * levels
    * constants
    * variables
  * default_scalars
  * module_name: `str` - May link to `CharacterModule.module_scalar.module_name`
* abilities_scalars: `list[dict]`
  * `<index>`: `int` - Links to `CharacterModule.abilities_refs.__index__`
  * `<element>`: `dict`
    * primary_stat_ref
    * secondary_stat_ref
    * levels
    * default_scalars

# CharacterModule.json
* id: `str`
* module_scalar
  * module_name
  * default_scalars
* abilities_refs: list
  * `<index>`: `int`
  * `<element>`: `str` - Links to `Ability.id`

# Ability.json
* id

# Misc notes
* Torso core modules use abilities_scalars
  * name and description are in Ability.json
* Non-core gear modules use module_scalars
  * name and description are in Module.json
* Non-ability modules like weapons/shoulders use module_scalars
  * name and description are in Module.json