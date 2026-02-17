from copy import deepcopy
from typing import Any, Dict, Optional, Tuple

EXCLUDED_LOCKS = {
    "OwnerPadlock",
    "OwnerTimerPadlock",
    "LoversPadlock",
    "LoversTimerPadlock",
}

LOCK_PROPERTY_KEYS = {
    "LockedBy",
    "LockMemberNumber",
    "CombinationNumber",
    "Password",
    "EnableRandomInput",
    "MemberNumberList",
}


def resolve_member_number(
    player: Dict[str, Any],
    others: Dict[int, Dict[str, Any]],
    current_chatroom: Optional[Dict[str, Any]],
    member_number: int,
    player_index: int,
) -> Tuple[Optional[int], Optional[str]]:
    if member_number > 0:
        return member_number, None

    if player_index < 0:
        return None, "provide member_number > 0 or player_index >= 0"

    room = current_chatroom or {}
    player_order = room.get("PlayerOrder")
    if isinstance(player_order, list) and player_index < len(player_order):
        resolved = player_order[player_index]
        if isinstance(resolved, int) and resolved > 0:
            return resolved, None

    members: list[int] = []
    self_no = player.get("MemberNumber")
    if isinstance(self_no, int):
        members.append(self_no)
    for no in sorted(others.keys()):
        if isinstance(no, int):
            members.append(no)

    if player_index >= len(members):
        return None, f"player_index {player_index} out of range; current member_count={len(members)}"
    return members[player_index], None


def get_cached_character(
    player: Dict[str, Any],
    others: Dict[int, Dict[str, Any]],
    member_number: int,
) -> Optional[Dict[str, Any]]:
    if player.get("MemberNumber") == member_number:
        return player
    return others.get(member_number)


def normalize_appearance_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None

    group = item.get("Group") or item.get("G")
    name = item.get("Name") or item.get("A")
    if not isinstance(group, str) or not isinstance(name, str):
        return None

    color = item.get("Color")
    if color is None:
        color = item.get("C", "Default")

    difficulty = item.get("Difficulty")
    if not isinstance(difficulty, int):
        difficulty = item.get("D")
    if not isinstance(difficulty, int):
        difficulty = 0

    prop = item.get("Property")
    if prop is None:
        prop = item.get("P")
    craft = item.get("Craft")

    return {
        "group": group,
        "name": name,
        "color": color if color is not None else "Default",
        "difficulty": difficulty,
        "property": deepcopy(prop) if isinstance(prop, dict) else None,
        "craft": deepcopy(craft) if isinstance(craft, dict) else None,
    }


def build_item_update_payload(
    target: int,
    group: str,
    name: Optional[str],
    color: Any = "Default",
    difficulty: int = 0,
    prop: Optional[Dict[str, Any]] = None,
    craft: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "Target": target,
        "Group": group,
        "Color": color if color is not None else "Default",
        "Difficulty": difficulty if isinstance(difficulty, int) else 0,
    }
    if isinstance(name, str):
        payload["Name"] = name
    if isinstance(prop, dict):
        payload["Property"] = prop
    if isinstance(craft, dict):
        payload["Craft"] = craft
    return payload


def strip_lock_properties(prop: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    new_prop = deepcopy(prop)
    for key in LOCK_PROPERTY_KEYS:
        new_prop.pop(key, None)
    return new_prop or None
