import sys
import os
import re

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from parsers.module import Module
from parsers.module_type import ModuleType
from parsers.character_preset import CharacterPreset
from parsers.pilot import Pilot
from parsers.pilot_talent import PilotTalent
from parsers.localization import Localization
from parsers.virtual_bot import VirtualBot
from parsers.module_group import ModuleGroup
from parsers.object import ParseObject

CORE_MODULE_CATEGORIES = [
    'DA_ModuleCategory_Chassis.0',
    'DA_ModuleCategory_Torso.0',
    'DA_ModuleCategory_Shoulder.0',
]

PILOT_TYPE_LEGENDARY_REF = 'OBJID_PilotType::DA_PilotType_Legendary.0'

def slugify(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-')

def get_default_string(localization_key):
    en = Localization.objects.get('en')
    if not en:
        return ""
    return en.localize_from_name(localization_key)

def ref_to_id(ref):
    if not ref or '::' not in ref:
        return ref
    return ref.split('::')[1]

def is_core_module(module):
    module_type_ref = getattr(module, 'module_type_ref', None)
    if not module_type_ref:
        return False
    
    module_type = ModuleType.get_from_ref(module_type_ref)
    if not module_type or not hasattr(module_type, 'module_category_ref'):
        return False
    
    category_id = ref_to_id(module_type.module_category_ref)
    return category_id in CORE_MODULE_CATEGORIES

def enrich():
    logger.info("Starting enrichment phase...")
    
    # 1. Module Groups
    ModuleGroup.generate_all()
    for module in Module.objects.values():
        module_type_ref = getattr(module, 'module_type_ref', None)
        if module_type_ref:
            type_id = ref_to_id(module_type_ref)
            group_id = ModuleGroup.get_group_id_for_type(type_id)
            if group_id:
                module.module_group_ref = ModuleGroup.id_to_ref(group_id)

    # 2. Virtual Bots & Bot Refs
    enrich_modules_with_bots()

    # 3. Pilot Talents
    enrich_pilot_talents()

def enrich_modules_with_bots():
    logger.info("Generating Virtual Bots and enriching modules with bot_ref...")
    
    # Filter factory presets
    factory_presets = {id: p for id, p in CharacterPreset.objects.items() if getattr(p, 'is_factory_preset', False)}
    
    # Deterministic order
    sorted_preset_ids = sorted(factory_presets.keys())
    
    core_module_to_bot_id = {}
    virtual_bots = {}

    all_core_module_ids = [id for id, m in Module.objects.items() if is_core_module(m)]

    for module_id in all_core_module_ids:
        if module_id in core_module_to_bot_id:
            continue

        # Find first factory preset that uses this core module
        first_preset_id = None
        for pid in sorted_preset_ids:
            preset = factory_presets[pid]
            if any(ref_to_id(m['module_ref']) == module_id for m in preset.modules):
                first_preset_id = pid
                break
        
        if first_preset_id:
            preset = factory_presets[first_preset_id]
            bot_name_str = get_default_string(preset.name) or first_preset_id
            bot_id = slugify(bot_name_str)

            # Map all core modules in this preset to this bot_id
            for m_data in preset.modules:
                m_id = ref_to_id(m_data['module_ref'])
                if m_id in Module.objects and is_core_module(Module.objects[m_id]):
                    if m_id not in core_module_to_bot_id:
                        core_module_to_bot_id[m_id] = bot_id

            if bot_id not in virtual_bots:
                # Calculate has_distinct_shoulders for this bot's presets
                # Actually, the logic in Site calculates it per preset, but here we might want it per bot?
                # The analysis says "Modules with ... has_distinct_shoulders fields".
                # It's used by getObjRefData to decide if side prefix is needed.
                
                # Let's check if the first preset has distinct shoulders
                shoulderL = next((m for m in preset.modules if m.get('socket_name') == 'Shoulder_L'), None)
                shoulderR = next((m for m in preset.modules if m.get('socket_name') == 'Shoulder_R'), None)
                has_distinct = bool(shoulderL and shoulderR and shoulderL['module_ref'] != shoulderR['module_ref'])

                virtual_bots[bot_id] = VirtualBot(
                    id=bot_id,
                    name=preset.name,
                    character_type=getattr(preset, 'character_type', 'Unknown'),
                    core_modules=[],
                    factory_presets=[],
                    iconPath=getattr(preset, 'icon', None)
                )
                # We'll set a temporary attribute on the bot object to store has_distinct
                virtual_bots[bot_id]._has_distinct_shoulders = has_distinct

            # Add core modules to bot
            for m_data in preset.modules:
                m_id = ref_to_id(m_data['module_ref'])
                if m_id in Module.objects and is_core_module(Module.objects[m_id]):
                    if m_id not in virtual_bots[bot_id].core_modules:
                        virtual_bots[bot_id].core_modules.append(m_id)

    # Associate factory presets with bots
    for pid, preset in factory_presets.items():
        assigned_bot_id = None
        for m_data in preset.modules:
            m_id = ref_to_id(m_data['module_ref'])
            if m_id in core_module_to_bot_id:
                assigned_bot_id = core_module_to_bot_id[m_id]
                break
        
        if assigned_bot_id and assigned_bot_id in virtual_bots:
            if pid not in virtual_bots[assigned_bot_id].factory_presets:
                virtual_bots[assigned_bot_id].factory_presets.append(pid)

    # Finally, enrich Module objects with bot_ref and has_distinct_shoulders
    for module_id, module in Module.objects.items():
        bot_id = core_module_to_bot_id.get(module_id)
        if bot_id:
            module.virtual_bot_ref = VirtualBot.id_to_ref(bot_id)
            bot = virtual_bots.get(bot_id)
            if bot and getattr(bot, '_has_distinct_shoulders', False):
                module.has_distinct_shoulders = True
            
            # Clean up temporary attribute
            if bot and hasattr(bot, '_has_distinct_shoulders'):
                # We leave it for now if needed, but we don't want it in final JSON.
                # Actually to_dict() will include all __dict__ keys.
                pass

    # Clean up the temporary attribute from virtual bots before export
    for bot in virtual_bots.values():
        if hasattr(bot, '_has_distinct_shoulders'):
            del bot._has_distinct_shoulders

def enrich_pilot_talents():
    logger.info("Enriching pilot talents...")
    
    # Initialize talent entries
    for talent in PilotTalent.objects.values():
        talent.pilots_with_this_talent = []

    # Scan all pilots
    for pilot in Pilot.objects.values():
        if not hasattr(pilot, 'levels'):
            continue
            
        for level_index, level_entry in enumerate(pilot.levels):
            talents_refs = level_entry.get('talents_refs', [])
            for talent_index, talent_ref in enumerate(talents_refs):
                talent_id = ref_to_id(talent_ref)
                talent = PilotTalent.objects.get(talent_id)
                
                if talent:
                    # Basic info
                    pilot_info = {
                        'pilot_ref': pilot.to_ref(),
                        'talentIndex': talent_index
                    }
                    talent.pilots_with_this_talent.append(pilot_info)

                    # Set talent_type_ref and level if not set
                    if not hasattr(talent, 'talent_type_ref'):
                        talent.talent_type_ref = level_entry.get('talent_type_ref')
                    else:
                        # verify the talent type is the same
                        if talent.talent_type_ref != level_entry.get('talent_type_ref'):
                            logger.error(f"GAME DATA CHANGE: Pilot '{pilot.first_name.en} {pilot.last_name.en}' has inconsistent talent types for talent '{talent.name.en}': expected {talent.talent_type_ref}, got {level_entry.get('talent_type_ref')}")
                    
                    if not hasattr(talent, 'level'):
                        talent.level = level_index + 1
                    else: 
                        # verify the level is the same
                        if talent.level != level_index + 1:
                            logger.error(f"GAME DATA CHANGE: Pilot '{pilot.first_name.en} {pilot.last_name.en}' has inconsistent levels for talent '{talent.name.en}': expected {talent.level}, got {level_index + 1}")

    # Sort pilots_with_this_talent: hero pilots first, then by name
    for talent in PilotTalent.objects.values():
        def sort_key(info):
            pilot = Pilot.get_from_ref(info['pilot_ref'])
            is_hero = getattr(pilot, 'pilot_type_ref', None) == PILOT_TYPE_LEGENDARY_REF
            name = get_default_string(getattr(pilot, 'first_name', {})) or ""
            return (not is_hero, name)
        
        talent.pilots_with_this_talent.sort(key=sort_key)
