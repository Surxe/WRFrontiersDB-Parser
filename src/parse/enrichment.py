import sys
import os
import re

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from parsers.module import Module
from parsers.module_type import ModuleType
from parsers.module_category import ModuleCategory
from parsers.character_preset import CharacterPreset
from parsers.pilot import Pilot
from parsers.pilot_talent import PilotTalent
from parsers.localization import Localization
from parsers.virtual_bot import VirtualBot
from parsers.module_group import ModuleGroup
from parsers.bot_ai_preset import BotAIPreset
from parsers.drop_team import DropTeam
from parsers.module_socket_type import ModuleSocketType
from exclusive_module_socket_matching import (
    ExclusiveAssignmentError,
    resolve_exclusive_module_socket_assignments,
)
from parsers.rarity_upgrade_cost import RarityUpgradeCost

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

def is_virtual_bot_module(module):
    module_type_ref = getattr(module, 'module_type_ref', None)
    if not module_type_ref:
        return False
    
    # Get the module group for this module type
    group_id = ModuleGroup.get_group_id_for_type(ref_to_id(module_type_ref))
    if not group_id:
        return False
    
    # Check if this module group is marked as a virtual bot module
    module_group = ModuleGroup.objects.get(group_id)
    if not module_group:
        return False
    
    return getattr(module_group, 'virtual_bot_module', False)

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

    # 2. Module socket exclusivity
    enrich_module_socket_type_exclusivity()

    # 3. Character Presets - Weapon Module Refs
    enrich_character_presets_with_weapon_refs()

    # 4. Virtual Bots & Bot Refs
    enrich_modules_with_bots()

    # 5. Pilot Talents
    enrich_pilot_talents()

    # 6. Rarity Upgrade Costs
    enrich_rarity_upgrade_costs()

def enrich_module_socket_type_exclusivity():
    logger.info("Enriching module socket type exclusivity...")
    socket_to_types = {}
    for socket in ModuleSocketType.objects.values():
        compatible_refs = getattr(socket, 'compatible_module_types_refs', None) or []
        socket_to_types[socket.id] = {ref_to_id(ref) for ref in compatible_refs}

    try:
        socket_to_type, type_to_socket = resolve_exclusive_module_socket_assignments(socket_to_types)
    except ExclusiveAssignmentError as exc:
        logger.error(f"Failed to resolve exclusive module socket assignments: {exc}")
        raise

    for socket_id, type_id in socket_to_type.items():
        ModuleSocketType.objects[socket_id].exclusive_module_type_ref = ModuleType.id_to_ref(type_id)
    for type_id, socket_id in type_to_socket.items():
        ModuleType.objects[type_id].exclusive_module_socket_type_ref = ModuleSocketType.id_to_ref(socket_id)

def enrich_character_presets_with_weapon_refs():
    logger.info("Enriching character presets with weapon module refs...")
    
    for preset in CharacterPreset.objects.values():
        weapon_module_ref = None
        
        # Iterate over modules to find the weapon
        for module_data in preset.modules:
            module_ref = module_data.get('module_ref')
            if not module_ref:
                continue
                
            module_id = ref_to_id(module_ref)
            module = Module.objects.get(module_id)
            
            if not module:
                continue
                
            # Check if this module has ModuleCategory = Weapon
            module_type_ref = getattr(module, 'module_type_ref', None)
            if module_type_ref:
                module_type_id = ref_to_id(module_type_ref)
                module_type = ModuleType.objects.get(module_type_id)
                
                if module_type:
                    module_category_ref = getattr(module_type, 'module_category_ref', None)
                    if module_category_ref:
                        module_category_id = ref_to_id(module_category_ref)
                        module_category = ModuleCategory.objects.get(module_category_id)
                        
                        if module_category and hasattr(module_category, 'name'):
                            category_name = getattr(module_category.name, 'Key', '') if hasattr(module_category.name, 'Key') else str(module_category.name)
                            if category_name == 'DA_ModuleCategory_Weapon' or 'Weapon' in category_name:
                                weapon_module_ref = module_ref
                                break
        
        # Set the weapon_module_ref on the preset
        if weapon_module_ref:
            preset.weapon_module_ref = weapon_module_ref

def enrich_modules_with_bots():
    logger.info("Generating Virtual Bots and enriching modules with virtual_bot_ref and shoulder_side...")
    
    # Filter factory presets
    factory_presets = {id: p for id, p in CharacterPreset.objects.items() if getattr(p, 'is_factory_preset', False)}
    
    # Deterministic order
    sorted_preset_ids = sorted(factory_presets.keys())
    
    core_module_to_bot_id = {}
    module_id_to_sides = {} # {module_id: set(['L', 'R'])}
    virtual_bots = {}

    all_virtual_bot_module_ids = [id for id, m in Module.objects.items() if is_virtual_bot_module(m)]

    for module_id in all_virtual_bot_module_ids:
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
            
            # Find the Chassis or Torso module to use as the bot's name
            bot_name_localization = preset.name # Fallback to preset name
            for m_data in preset.modules:
                m_id = ref_to_id(m_data['module_ref'])
                if m_id in Module.objects:
                    module = Module.objects[m_id]
                    group_ref = getattr(module, 'module_group_ref', None)
                    if group_ref and ('chassis' in group_ref.lower() or 'torso' in group_ref.lower()):
                        if hasattr(module, 'name'):
                            bot_name_localization = module.name
                            break

            bot_name_str = get_default_string(bot_name_localization) or first_preset_id
            bot_id = slugify(bot_name_str)

            # Map all virtual bot modules in this preset to this bot_id
            for m_data in preset.modules:
                m_id = ref_to_id(m_data['module_ref'])
                if m_id in Module.objects and is_virtual_bot_module(Module.objects[m_id]):
                    if m_id not in core_module_to_bot_id:
                        core_module_to_bot_id[m_id] = bot_id

            if bot_id not in virtual_bots:
                # Calculate has_distinct_shoulders for this bot's presets
                shoulderL = next((m for m in preset.modules if m.get('socket_name') == 'Shoulder_L'), None)
                shoulderR = next((m for m in preset.modules if m.get('socket_name') == 'Shoulder_R'), None)
                has_distinct = bool(shoulderL and shoulderR and shoulderL['module_ref'] != shoulderR['module_ref'])

                virtual_bots[bot_id] = VirtualBot(
                    id=bot_id,
                    name=bot_name_localization,
                    character_type=getattr(preset, 'character_type', 'Mech'),
                    core_module_refs=[],
                    factory_preset_refs=[],
                    has_distinct_shoulders=has_distinct,
                    icon_path=getattr(preset, 'icon', None)
                )

            # Add virtual bot modules to bot
            for m_data in preset.modules:
                m_id = ref_to_id(m_data['module_ref'])
                if m_id in Module.objects and is_virtual_bot_module(Module.objects[m_id]):
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

    # Check AI bots for titan weapons and add them to corresponding virtual bots
    logger.info("Checking AI bots for titan weapons...")
    logger.info(f"Found {len(BotAIPreset.objects)} AI bots")
    
    for bot_ai in BotAIPreset.objects.values():
        if not hasattr(bot_ai, 'drop_teams_refs'):
            continue
            
        for drop_team_ref in bot_ai.drop_teams_refs:
            drop_team_id = ref_to_id(drop_team_ref)
            drop_team = DropTeam.objects.get(drop_team_id)
            
            if not drop_team or not hasattr(drop_team, 'character_presets_refs'):
                continue
                
            # Find character presets in this drop team
            for preset_ref in drop_team.character_presets_refs:
                preset_id = ref_to_id(preset_ref)
                preset = CharacterPreset.objects.get(preset_id)
                
                if not preset or getattr(preset, 'is_factory_preset', False):
                    continue
                    
                # Check if this preset has titan weapons
                bot_name = get_default_string(preset.name) or preset_id
                bot_slug = slugify(bot_name)
                
                # Look for titan weapons in this preset
                for m_data in preset.modules:
                    m_id = ref_to_id(m_data['module_ref'])
                    if m_id in Module.objects:
                        module = Module.objects[m_id]
                        module_type_ref = getattr(module, 'module_type_ref', None)
                        if module_type_ref:
                            type_id = ref_to_id(module_type_ref)
                            group_id = ModuleGroup.get_group_id_for_type(type_id)
                            if group_id == 'titan-weapon':
                                # Find the virtual bot with the same name
                                if bot_slug in virtual_bots:
                                    m_ref = Module.id_to_ref(m_id)
                                    if m_ref not in virtual_bots[bot_slug].core_module_refs:
                                        virtual_bots[bot_slug].core_module_refs.append(m_ref)
                                        # Also update the core_module_to_bot_id mapping
                                        core_module_to_bot_id[m_id] = bot_slug
                                        logger.info(f"Added titan weapon {m_id} to virtual bot {bot_slug} from AI bot {bot_name}")

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
                            logger.warning(f"GAME DATA CHANGE: Pilot '{pilot.id} {pilot.first_name["en"]} {pilot.last_name["en"] if getattr(pilot, "last_name", None) else ''}' has inconsistent talent types for talent '{talent.name["en"]}': expected {talent.talent_type_ref}, got {level_entry.get('talent_type_ref')}")
                    
                    if not hasattr(talent, 'level'):
                        talent.level = level_index + 1
                    else: 
                        # verify the level is the same
                        if talent.level != level_index + 1:
                            logger.warning(f"GAME DATA CHANGE: Pilot '{pilot.id} {pilot.first_name["en"]} {pilot.last_name["en"] if getattr(pilot, "last_name", None) else ''}' has inconsistent levels for talent '{talent.name["en"]}': expected {talent.level}, got {level_index + 1}")

    # Sort pilots_with_this_talent: hero pilots first, then by name
    for talent in PilotTalent.objects.values():
        def sort_key(info):
            pilot = Pilot.get_from_ref(info['pilot_ref'])
            is_hero = getattr(pilot, 'pilot_type_ref', None) == PILOT_TYPE_LEGENDARY_REF
            name = get_default_string(getattr(pilot, 'first_name', {})) or ""
            return (not is_hero, name)
        
        talent.pilots_with_this_talent.sort(key=sort_key)

def enrich_rarity_upgrade_costs():
    logger.info("Enriching Rarity Upgrade Costs...")
    from analysis import Analysis, INTEL_CURRENCY_REF, ALLOY_CURRENCY_REF, DISCOUNT_COST_MAP
    
    # Instantiate Analysis to get the standard cost map
    analysis = Analysis()
    
    for rarity_ref, levels_data in analysis.standard_cost_and_scrap.items():
        costs = {}
        discount_map = DISCOUNT_COST_MAP.get(rarity_ref, {})
        intel_discounts = discount_map.get(INTEL_CURRENCY_REF, {})
        alloy_discounts = discount_map.get(ALLOY_CURRENCY_REF, {})
        
        for level_int, currency_data in levels_data.items():
            level_str = str(level_int)
            costs[level_str] = {}
            
            # Alloy / Salvage
            alloy_standard = currency_data.get(ALLOY_CURRENCY_REF, {}).get('upgrade_cost', 0)
            alloy_discounted = alloy_discounts.get(int(level_int))
            costs[level_str]['salvage'] = {
                'standard': alloy_standard,
                'discounted': alloy_discounted
            }
            
            # Intel
            intel_standard = currency_data.get(INTEL_CURRENCY_REF, {}).get('upgrade_cost', 0)
            intel_discounted = intel_discounts.get(int(level_int))
            costs[level_str]['intel'] = {
                'standard': intel_standard,
                'discounted': intel_discounted
            }
            
        RarityUpgradeCost(id=rarity_ref, rarity_ref=rarity_ref, costs=costs)
