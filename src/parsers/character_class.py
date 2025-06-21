# Add parent dirs to sys path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.object import Object

from utils import parse_badge_visual_info, parse_localization

class CharacterClass(Object):
    objects = dict()  # Dictionary to hold all Class instances

    def _parse(self):
        props = self.source_data["Properties"]
        self.image_id, self.tint_hex = parse_badge_visual_info(props["BadgeVisualInfo"])

        self.name = parse_localization(props["Name"])

        self.description = parse_localization(props["Description"])
        