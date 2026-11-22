"""The game's collision profiles and channels, from the cooked config, and the robot-block test.

UE builds each profile from ``[/Script/Engine.CollisionProfile]`` in ``Engine/Config/BaseEngine.ini``
then the game's ``DefaultEngine.ini`` (``UCollisionProfile::LoadProfileConfig`` and ``FillProfileData``,
``Engine/Private/Collision/CollisionProfile.cpp``):

- the default response container: every channel Block, except ``EngineTraceChannel1`` (the editor
  gizmo channel, Ignore), then each game channel's ``DefaultChannelResponses`` response;
- per profile: that container, then its ``CustomResponses``, then its ``EditProfiles`` entry. A
  response written without ``Response=`` is Block (``FResponseChannel``'s default).

A robot's movement capsule uses the stock ``Pawn`` profile (``ACharacter``'s constructor; WRF's
``ASCharacter`` and ``BP_Character`` change nothing) and sweeps on its own channel. A query hit blocks
when both sides block: the capsule blocks the other's object type, and the other blocks ``Pawn``.
"""
import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional

ENGINE_CHANNELS = (["WorldStatic", "WorldDynamic", "Pawn", "Visibility", "Camera", "PhysicsBody", "Vehicle", "Destructible"]
                   + [f"EngineTraceChannel{i}" for i in range(1, 7)] + [f"GameTraceChannel{i}" for i in range(1, 19)])
CHANNEL_COUNT = 32
PAWN = 2
QUERY_ENABLED = {"QueryOnly", "QueryAndPhysics", "QueryAndProbe"}
ROBOT_PROFILE = "Pawn"
CUSTOM = "Custom"
_SECTION = "[/Script/Engine.CollisionProfile]"
CONFIG_FILES = ("Engine/Config/BaseEngine.ini", "WRFrontiers/Config/DefaultEngine.ini")


def parse_struct(text: str):
    """A UE config struct value, ``(Name="X",List=((A=1),(A=2)),Flag=)``, as dicts, lists and strings."""
    value, _ = _parse_value(text, 0)
    return value


def _parse_value(text: str, i: int):
    if i >= len(text) or text[i] in ",)":
        return "", i
    if text[i] == '"':
        end = text.index('"', i + 1)
        return text[i + 1:end], end + 1
    if text[i] != "(":
        end = i
        while end < len(text) and text[end] not in ",)":
            end += 1
        return text[i:end], end
    i += 1
    keyed: Dict[str, object] = {}
    items: List[object] = []
    while i < len(text) and text[i] != ")":
        match = re.match(r"([A-Za-z_][A-Za-z_0-9]*)=", text[i:])
        if match:
            i += match.end()
            keyed[match.group(1)], i = _parse_value(text, i)
        else:
            item, i = _parse_value(text, i)
            items.append(item)
        if i < len(text) and text[i] == ",":
            i += 1
    return (keyed if keyed or not items else items), i + 1


def _section_lines(path: Path) -> List[str]:
    lines, inside = [], False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if line.startswith("["):
            inside = line == _SECTION
        elif inside and "=" in line and not line.startswith(";"):
            lines.append(line)
    return lines


def layered_arrays(texts: Iterable[List[str]]) -> Dict[str, List[str]]:
    """Array keys of the section after UE's layering: ``+`` adds a value not yet there, ``-`` removes
    it, ``.`` adds it even when there, and a bare key adds it."""
    arrays: Dict[str, List[str]] = {}
    for lines in texts:
        for line in lines:
            op = line[0] if line[0] in "+-." else ""
            key, value = line[len(op):].split("=", 1)
            values = arrays.setdefault(key.strip(), [])
            if op == "-":
                arrays[key.strip()] = [existing for existing in values if existing != value]
            elif op == "+" and value in values:
                continue
            else:
                values.append(value)
    return arrays


def response_name(value: Optional[str]) -> str:
    """``ECR_Ignore`` / ``ECollisionResponse::ECR_Ignore`` / ``Ignore`` -> ``Ignore``; empty is Block."""
    if not value:
        return "Block"
    return str(value).split("::")[-1].removeprefix("ECR_")


def enabled_name(value) -> str:
    """``ECollisionEnabled::QueryAndPhysics`` -> ``QueryAndPhysics``."""
    return str(value).split("::")[-1]


class CollisionProfiles:
    """Profiles, channel names and the default responses of the game's config."""

    def __init__(self, arrays: Dict[str, List[str]]) -> None:
        self.channel_names = list(ENGINE_CHANNELS)
        default = ["Block"] * CHANNEL_COUNT
        default[8] = "Ignore"  # COLLISION_GIZMO = ECC_EngineTraceChannel1 (EngineTypes.h)
        for entry in arrays.get("DefaultChannelResponses", []):
            setup = parse_struct(entry)
            index = self.channel_index(setup["Channel"])
            if setup.get("Name"):
                self.channel_names[index] = setup["Name"]
            default[index] = response_name(setup.get("DefaultResponse"))
        self.default_responses = default

        self.redirects = {}
        for entry in arrays.get("ProfileRedirects", []):
            redirect = parse_struct(entry)
            self.redirects[redirect["OldName"]] = redirect["NewName"]

        edits: Dict[str, list] = {}
        for entry in arrays.get("EditProfiles", []):
            edit = parse_struct(entry)
            edits[edit["Name"]] = list(edit.get("CustomResponses") or [])

        self.profiles: Dict[str, dict] = {}
        for entry in arrays.get("Profiles", []):
            profile = parse_struct(entry)
            responses = list(default)
            for custom in list(profile.get("CustomResponses") or []) + edits.get(profile["Name"], []):
                self._apply(responses, custom)
            object_type = profile.get("ObjectTypeName") or "WorldStatic"
            self.profiles[profile["Name"]] = {
                "enabled": enabled_name(profile.get("CollisionEnabled", "QueryAndPhysics")),
                "object_type": self.channel_names.index(object_type) if object_type in self.channel_names else 0,
                "responses": responses,
            }

    @classmethod
    def from_config(cls, config_dir) -> "CollisionProfiles":
        """From the export's ``config/`` directory (``map-export/config``)."""
        config_dir = Path(config_dir)
        return cls(layered_arrays(_section_lines(config_dir / name) for name in CONFIG_FILES))

    def _apply(self, responses: List[str], custom) -> None:
        if isinstance(custom, dict) and custom.get("Channel") in self.channel_names:
            responses[self.channel_names.index(custom["Channel"])] = response_name(custom.get("Response"))

    @staticmethod
    def channel_index(value) -> int:
        """``ECollisionChannel::ECC_GameTraceChannel7`` or ``ECC_Pawn`` -> its index."""
        name = str(value).split("::")[-1].removeprefix("ECC_")
        return ENGINE_CHANNELS.index(name)

    def profile(self, name: Optional[str]) -> Optional[dict]:
        if not name or name == CUSTOM:
            return None
        return self.profiles.get(self.redirects.get(name, name))

    def responses(self, response_array: Iterable[dict], base: Optional[List[str]] = None) -> List[str]:
        """A ``ResponseArray`` ({channel display name: response} or [{Channel, Response}]) over the
        default container (``FCollisionResponse::UpdateResponseContainerFromArray``)."""
        responses = list(self.default_responses if base is None else base)
        items = response_array.items() if isinstance(response_array, dict) else (
            (entry.get("Channel"), entry.get("Response")) for entry in response_array)
        for channel, response in items:
            if channel in self.channel_names:
                responses[self.channel_names.index(channel)] = response_name(response)
        return responses

    def robot(self) -> dict:
        robot = self.profile(ROBOT_PROFILE)
        if robot is None:
            raise ValueError(f"No {ROBOT_PROFILE} collision profile in the config")
        return robot

    def blocks_robot(self, collision: dict) -> bool:
        """Whether a resolved collision (``enabled``, ``object_type``, ``responses``) blocks a robot's sweep."""
        robot = self.robot()
        return (collision["enabled"] in QUERY_ENABLED
                and robot["responses"][collision["object_type"]] == "Block"
                and collision["responses"][PAWN] == "Block")
