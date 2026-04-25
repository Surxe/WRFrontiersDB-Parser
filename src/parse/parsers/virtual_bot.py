# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

"""
Virtual Bot represents the a robot the way its referenced by the community.

"Woah that new Garuda bot looks awesome!" -> refers to the modules that are specific to Garuda, i.e. the virtual bot modules, Torso, Chassis, Shoulder(s), and Titan Weapon

Virtual Bot would be named Garuda. In addition to storing the virtual bot modules, it would specify if it has two different shoulders (like titans) and factory presets that use these virtual bot modules.
"""

class VirtualBot(ParseObject):
    objects = dict()

    def __init__(self, id: str, name: dict, character_type: str, core_module_refs: list, factory_preset_refs: list, has_distinct_shoulders: bool, icon_path: str = None):
        self.id = id
        self.name = name
        self.character_type = character_type
        self.core_module_refs = core_module_refs
        self.factory_preset_refs = factory_preset_refs
        self.has_distinct_shoulders = has_distinct_shoulders
        self.icon_path = icon_path
        
        self.objects[id] = self

    def _parse(self):
        # VirtualBot is a synthetic object, it doesn't parse from a single source asset.
        pass
