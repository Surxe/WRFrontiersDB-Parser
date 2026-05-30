"""
Exclusive ModuleSocketType ↔ ModuleType matching.

Game data defines socket → compatible module types (1:many). This module derives a
deterministic "most exclusive" pairing by repeatedly assigning sockets that have
only one remaining compatible type after already-assigned types are removed from
each socket's pool.

Algorithm (multi-pass until fixed point)
----------------------------------------
Each pass:
  1. For every unassigned socket with exactly one compatible type in game data,
     assign that type (even if another socket already uses it). The reverse
     type → socket map keeps the first socket encountered in input order.
  2. For every other unassigned socket, compute:
         remaining = compatible_types − {types already assigned to other sockets}
  3. Assign any such socket where len(remaining) == 1 to that sole type.
  4. If a multi-option socket would claim a type already assigned in this pass
     to another multi-option socket, raise ExclusiveAssignmentError.
  5. If any assignments were made, start another pass from step 1.
  6. If no assignments were made and unassigned sockets remain, raise
     ExclusiveAssignmentError (ambiguous or unsatisfiable data).

Light / heavy weapon example
----------------------------
  light_socket  compatible: {Weapon}
  heavy_socket  compatible: {Weapon, WeaponHeavy}

  Pass 0: light_socket has one option → assign Weapon to light_socket.
  Pass 1: heavy_socket pool becomes {WeaponHeavy} after pruning Weapon →
          assign WeaponHeavy to heavy_socket.

Reverse mapping: Weapon → light_socket, WeaponHeavy → heavy_socket.

Shoulder L / R example
----------------------
  shoulder_l_socket  compatible: {Shoulder}
  shoulder_r_socket  compatible: {Shoulder}

  Pass 0: both sockets have one option → assign Shoulder to each.
  Reverse mapping: Shoulder → shoulder_l_socket (first in input order).
"""


class ExclusiveAssignmentError(Exception):
    """Raised when exclusive socket ↔ type assignment cannot be completed."""


def resolve_exclusive_module_socket_assignments(
    socket_to_compatible_type_ids: dict[str, set[str]],
) -> tuple[dict[str, str], dict[str, str]]:
    """
    Resolve exclusive assignments between sockets and module types.

    Socket → type is many-to-one when multiple sockets share a single compatible
    type (e.g. left/right shoulder). Type → socket is one-to-one and uses the
    first socket in input order for shared types.

    Args:
        socket_to_compatible_type_ids: Maps socket id → set of compatible module type ids.

    Returns:
        (socket_id → type_id, type_id → socket_id)

    Raises:
        ExclusiveAssignmentError: If any socket cannot be uniquely assigned.
    """
    socket_to_type: dict[str, str] = {}
    type_to_socket: dict[str, str] = {}

    while True:
        assigned_types = set(type_to_socket.keys())
        progress = False

        for socket_id, compatible_types in socket_to_compatible_type_ids.items():
            if socket_id in socket_to_type:
                continue

            if not compatible_types:
                raise ExclusiveAssignmentError(
                    f"Socket '{socket_id}' has no compatible module types and cannot be assigned."
                )

            if len(compatible_types) == 1:
                type_id = next(iter(compatible_types))
                socket_to_type[socket_id] = type_id
                if type_id not in type_to_socket:
                    type_to_socket[type_id] = socket_id
                progress = True
                continue

            remaining = compatible_types - assigned_types

            if len(remaining) == 0:
                raise ExclusiveAssignmentError(
                    f"Socket '{socket_id}' has no remaining compatible module types after "
                    f"pruning already-assigned types. Compatible: {sorted(compatible_types)}, "
                    f"already assigned: {sorted(assigned_types & compatible_types)}."
                )

            if len(remaining) != 1:
                continue

            type_id = next(iter(remaining))
            if type_id in type_to_socket:
                raise ExclusiveAssignmentError(
                    f"Module type '{type_id}' would be assigned to both "
                    f"'{type_to_socket[type_id]}' and '{socket_id}'."
                )

            socket_to_type[socket_id] = type_id
            type_to_socket[type_id] = socket_id
            progress = True

        if progress:
            continue

        unassigned = [
            socket_id
            for socket_id in socket_to_compatible_type_ids
            if socket_id not in socket_to_type
        ]
        if not unassigned:
            break

        unresolved = {}
        for socket_id in unassigned:
            remaining = socket_to_compatible_type_ids[socket_id] - set(type_to_socket.keys())
            unresolved[socket_id] = sorted(remaining)

        details = "; ".join(
            f"{socket_id}: remaining {pools}"
            for socket_id, pools in unresolved.items()
        )
        raise ExclusiveAssignmentError(
            "Could not resolve exclusive module socket assignments. "
            f"Unassigned sockets and their remaining compatible types: {details}"
        )

    return socket_to_type, type_to_socket
