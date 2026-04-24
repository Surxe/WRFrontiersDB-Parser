# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
from parsers.object import ParseObject
from parsers.module_type import ModuleType

MODULE_TYPE_TO_GROUP = {
    # Titan torsos
    'DA_ModuleType_TitanAlphaTorso.0': 'titan-torsos',
    'DA_ModuleType_TitanGrimTorso.0': 'titan-torsos',
    'DA_ModuleType_TitanMatriarchTorso.0': 'titan-torsos',
    'DA_ModuleType_TitanNornaTorso.0': 'titan-torsos',
    'DA_ModuleType_TitanSpireTorso.0': 'titan-torsos',

    # Non-titan torsos
    'DA_ModuleType_Torso.0': 'non-titan-torsos',

    # Titan chassis
    'DA_ModuleType_TitanAlphaChassis.0': 'titan-chassis',
    'DA_ModuleType_TitanGrimChassis.0': 'titan-chassis',
    'DA_ModuleType_TitanMatriarchChassis.0': 'titan-chassis',
    'DA_ModuleType_TitanNornaChassis.0': 'titan-chassis',
    'DA_ModuleType_TitanSpireChassis.0': 'titan-chassis',

    # Non-titan chassis
    'DA_ModuleType_Chassis.0': 'non-titan-chassis',

    # Titan shoulders
    'DA_ModuleType_TitanAlphaShoulderL.0': 'titan-shoulder',
    'DA_ModuleType_TitanAlphaShoulderR.0': 'titan-shoulder',
    'DA_ModuleType_TitanGrimShoulderL.0': 'titan-shoulder',
    'DA_ModuleType_TitanGrimShoulderR.0': 'titan-shoulder',
    'DA_ModuleType_TitanMatriarchShoulderL.0': 'titan-shoulder',
    'DA_ModuleType_TitanMatriarchShoulderR.0': 'titan-shoulder',
    'DA_ModuleType_TitanNornaShoulderL.0': 'titan-shoulder',
    'DA_ModuleType_TitanNornaShoulderR.0': 'titan-shoulder',
    'DA_ModuleType_TitanSpireShoulderL.0': 'titan-shoulder',
    'DA_ModuleType_TitanSpireShoulderR.0': 'titan-shoulder',

    # Non-titan shoulders
    'DA_ModuleType_Shoulder.0': 'non-titan-shoulder',

    # Light weapons
    'DA_ModuleType_Weapon.0': 'light-weapon',

    # Heavy weapons
    'DA_ModuleType_WeaponHeavy.0': 'heavy-weapon',

    # Titan weapons
    'DA_ModuleType_TitanWeapon.0': 'titan-weapon',
    'DA_ModuleType_TitanWeaponAssault.0': 'titan-weapon',
    'DA_ModuleType_TitanWeaponFlanker.0': 'titan-weapon',
    'DA_ModuleType_TitanWeaponNorna.0': 'titan-weapon',
    'DA_ModuleType_TitanWeaponTactician.0': 'titan-weapon',
    'DA_ModuleType_TitanWeaponTank.0': 'titan-weapon',

    # Supply gear
    'DA_ModuleType_Ability2.0': 'supply-gear',
    'DA_ModuleType_Ability3.0': 'supply-gear',

    # Cycle gear
    'DA_ModuleType_Ability4.0': 'cycle-gear',
}

MODULE_GROUPS_DATA = {
    'titan-torsos': {
        'name': {'Key': 'CMP_Type_Titan_Torso', 'TableNamespace': 'Component_Tags'},
    },
    'titan-chassis': {
        'name': {'Key': 'CMP_Type_Titan_Chassis', 'TableNamespace': 'Component_Tags'},
    },
    'titan-shoulder': {
        'name': {'Key': 'GRP_TitanShoulders_Name', 'TableNamespace': 'ModuleGroups'},
    },
    'non-titan-torsos': {
        'name': {'Key': 'HNG_Torso', 'TableNamespace': 'Component_Tags'},
    },
    'non-titan-chassis': {
        'name': {'Key': 'HNG_Chassis', 'TableNamespace': 'Component_Tags'},
    },
    'non-titan-shoulder': {
        'name': {'Key': 'HNG_Shoulder', 'TableNamespace': 'Component_Tags'},
    },
    'titan-weapon': {
        'name': {'Key': 'CMP_Type_Titan_Weapon', 'TableNamespace': 'Component_Tags'},
    },
    'heavy-weapon': {
        'name': {'Key': 'HNG_HeavyWeapon', 'TableNamespace': 'Component_Tags'},
    },
    'light-weapon': {
        'name': {'Key': 'HNG_LightWeapon', 'TableNamespace': 'Component_Tags'},
    },
    'supply-gear': {
        'name': {'Key': 'HNG_Ability', 'TableNamespace': 'Component_Tags'},
    },
    'cycle-gear': {
        'name': {'Key': 'HNG_AbilityUlt', 'TableNamespace': 'Component_Tags'},
    },
}

class ModuleGroup(ParseObject):
    objects = dict()
    
    def __init__(self, id, name, sort_order, description=None):
        super().__init__(id)
        self.id = id
        self.name = name
        self.sort_order = sort_order
        if description:
            self.description = description

    def _parse(self):
        # ModuleGroup is a synthetic object, it doesn't parse game assets directly
        pass

    @classmethod
    def get_group_id_for_type(cls, type_id):
        return MODULE_TYPE_TO_GROUP.get(type_id)

    @classmethod
    def generate_all(cls):
        logger.info("Generating Module Groups...")
        index = 0
        for group_id, data in MODULE_GROUPS_DATA.items():
            # Supply gear needs a specific description, the rest can infer from arbitrary module type since theyre the same
            desc = None
            if group_id == 'supply-gear':
                m_type = ModuleType.objects.get('DA_ModuleType_Ability3.0')
                if m_type and hasattr(m_type, 'description'):
                    desc = m_type.description
            else:
                # find first type that maps to this group
                for type_id, target_group in MODULE_TYPE_TO_GROUP.items():
                    if target_group == group_id:
                        m_type = ModuleType.objects.get(type_id)
                        if m_type and hasattr(m_type, 'description'):
                            desc = m_type.description
                            break
            
            cls(
                id=group_id,
                name=data['name'],
                sort_order=index,
                description=desc
            )

            index += 1
