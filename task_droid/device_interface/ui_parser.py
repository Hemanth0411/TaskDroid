import xml.etree.ElementTree as ET
from typing import List

from task_droid.config import settings
from task_droid.shared.log_utils import log_message
from .elements import UIElement

def _generate_element_uid(elem: ET.Element) -> tuple[str, str | None]:
    """
    Creates a unique and descriptive ID for a UI element from its attributes.
    Also identifies a 'role_hint' for the element (e.g., search_bar).
    """
    bounds = elem.get("bounds", "[0,0][0,0]")
    try:
        coords = [int(c) for c in bounds.replace("][", ",").replace("[", "").replace("]", "").split(",")]
        elem_w, elem_h = (coords[2] - coords[0]), (coords[3] - coords[1])
    except (ValueError, IndexError):
        elem_w, elem_h = 0, 0

    # Main identifier
    res_id = elem.get("resource-id", "")
    if res_id:
        # Sanitize for use as a file name or identifier
        uid = res_id.replace("/", "_").replace(":", ".")
    else:
        # Fallback using class and size
        uid = f"{elem.get('class', 'NoClass')}_{elem_w}x{elem_h}"

    # Add content-desc for more uniqueness if it's short
    content_desc = elem.get("content-desc", "")
    if content_desc and len(content_desc) < 25:
        sanitized_desc = "".join(e for e in content_desc if e.isalnum() or e in "_-").replace(" ", "_")
        uid += f"_{sanitized_desc}"
    
    # --- Role Hint Identification ---
    role_hint = None
    text = elem.get("text", "").lower()
    elem_class = elem.get("class", "").lower()
    
    # Keywords for different roles
    search_kws = ["search", "query", "find"]
    nav_kws = ["nav", "navigation", "tab", "toolbar", "home", "profile", "menu"]

    # Combine all text-based attributes for keyword searching
    search_space = f"{res_id.lower()} {content_desc.lower()} {text}"

    if any(kw in search_space for kw in search_kws) or "searchview" in elem_class:
        role_hint = "search_bar"
    elif any(kw in search_space for kw in nav_kws) or "bottomnavigation" in elem_class or "tabwidget" in elem_class:
        role_hint = "nav_item"

    return uid, role_hint

def extract_interactive_elements(xml_path: str) -> List[UIElement]:
    """
    Traverses an XML layout file to find and extract all interactive
    (clickable or focusable) elements.

    Args:
        xml_path (str): The path to the UI XML dump file.

    Returns:
        List[UIElement]: A list of UIElement objects found on the screen.
    """
    if not xml_path or xml_path == "ERROR":
        return []

    interactive_elements = []
    try:
        # We parse the entire tree to build a parent map first
        tree = ET.parse(xml_path)
        root = tree.getroot()
        parent_map = {c: p for p in root.iter() for c in p}

        for elem in root.iter():
            if elem.get("clickable") == "true" or elem.get("focusable") == "true":
                bounds_str = elem.get("bounds")
                if not bounds_str:
                    continue
                
                try:
                    coords = [int(c) for c in bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")]
                    bbox = ((coords[0], coords[1]), (coords[2], coords[3]))

                    # Check for minimal distance to avoid overlapping labels
                    center_x, center_y = (coords[0] + coords[2]) // 2, (coords[1] + coords[3]) // 2
                    is_too_close = False
                    min_dist = settings.get_setting("device.min_element_dist", 20)
                    for existing_elem in interactive_elements:
                        ex, ey = (existing_elem.bbox[0][0] + existing_elem.bbox[1][0]) // 2, (existing_elem.bbox[0][1] + existing_elem.bbox[1][1]) // 2
                        if abs(center_x - ex) + abs(center_y - ey) < min_dist:
                            is_too_close = True
                            break
                    if is_too_close:
                        continue
                    
                    # Generate UID with parent context for better uniqueness
                    uid, role_hint = _generate_element_uid(elem)
                    parent = parent_map.get(elem)
                    if parent is not None:
                        parent_uid, _ = _generate_element_uid(parent)
                        uid = f"{parent_uid}.{uid}"
                    
                    # Combine attributes for the element
                    attributes = "clickable" if elem.get("clickable") == "true" else "focusable"
                    if role_hint:
                        attributes += f",{role_hint}"

                    interactive_elements.append(UIElement(uid=uid, bbox=bbox, attributes=attributes))

                except (ValueError, IndexError) as e:
                    log_message("WARNING", f"Could not parse bounds for element {elem.attrib}. Error: {e}", component="UIParser")
                    continue
    
    except ET.ParseError as e:
        log_message("ERROR", f"Failed to parse XML file at {xml_path}: {e}", component="UIParser", color="red")
        return []
    
    return interactive_elements