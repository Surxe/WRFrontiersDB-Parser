# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import ParseObject

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
