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
    logger.info("Generating Virtual Bots and enriching modules with virtual_bot_ref and shoulder_side...")
    
    # Filter factory presets
    factory_presets = {id: p for id, p in CharacterPreset.objects.items() if getattr(p, 'is_factory_preset', False)}
    
    # Deterministic order
    sorted_preset_ids = sorted(factory_presets.keys())
    
    core_module_to_bot_id = {}
    module_id_to_sides = {} # {module_id: set(['L', 'R'])}
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
                shoulderL = next((m for m in preset.modules if m.get('socket_name') == 'Shoulder_L'), None)
                shoulderR = next((m for m in preset.modules if m.get('socket_name') == 'Shoulder_R'), None)
                has_distinct = bool(shoulderL and shoulderR and shoulderL['module_ref'] != shoulderR['module_ref'])

                virtual_bots[bot_id] = VirtualBot(
                    id=bot_id,
                    name=preset.name,
                    character_type=getattr(preset, 'character_type', 'Mech'),
                    core_module_refs=[],
                    factory_preset_refs=[],
                    has_distinct_shoulders=has_distinct,
                    icon_path=getattr(preset, 'icon', None)
                )

            # Add core modules to bot
            for m_data in preset.modules:
                m_id = ref_to_id(m_data['module_ref'])
                if m_id in Module.objects and is_core_module(Module.objects[m_id]):
                    m_ref = Module.id_to_ref(m_id)
                    if m_ref not in virtual_bots[bot_id].core_module_refs:
                        virtual_bots[bot_id].core_module_refs.append(m_ref)
                    
                    # Track sides for shoulder modules
                    socket_name = m_data.get('socket_name', '')
                    if 'Shoulder_L' in socket_name:
                        module_id_to_sides.setdefault(m_id, set()).add('L')
                    elif 'Shoulder_R' in socket_name:
                        module_id_to_sides.setdefault(m_id, set()).add('R')

    # Associate factory presets with bots
    for pid, preset in factory_presets.items():
        assigned_bot_id = None
        for m_data in preset.modules:
            m_id = ref_to_id(m_data['module_ref'])
            if m_id in core_module_to_bot_id:
                assigned_bot_id = core_module_to_bot_id[m_id]
                break
        
        if assigned_bot_id and assigned_bot_id in virtual_bots:
            preset_ref = CharacterPreset.id_to_ref(pid)
            if preset_ref not in virtual_bots[assigned_bot_id].factory_preset_refs:
                virtual_bots[assigned_bot_id].factory_preset_refs.append(preset_ref)

    # Finally, enrich Module objects with virtual_bot_ref and shoulder_side
    for module_id, module in Module.objects.items():
        bot_id = core_module_to_bot_id.get(module_id)
        if bot_id:
            module.virtual_bot_ref = VirtualBot.id_to_ref(bot_id)
        
        # Add shoulder_side if it's a shoulder group and has a unique side
        group_ref = getattr(module, 'module_group_ref', None)
        if group_ref and ('shoulder' in group_ref.lower()):
            sides = module_id_to_sides.get(module_id, set())
            if len(sides) == 1:
                module.shoulder_side = list(sides)[0]

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
                        'talent_index': talent_index
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
