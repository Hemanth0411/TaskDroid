import xml.etree.ElementTree as ET
from typing import List

from task_droid.config import settings
from task_droid.shared.log_utils import log_message
from .elements import UIElement

def _generate_element_uid(elem: ET.Element) -> tuple[str, str | None]:
    bounds = elem.get("bounds", "[0,0][0,0]")
    try:
        coords = [int(c) for c in bounds.replace("][", ",").replace("[", "").replace("]", "").split(",")]
        elem_w, elem_h = (coords[2] - coords[0]), (coords[3] - coords[1])
    except (ValueError, IndexError):
        elem_w, elem_h = 0, 0
    res_id = elem.get("resource-id", "")
    if res_id:
        uid = res_id.replace("/", "_").replace(":", ".")
    else:
        uid = f"{elem.get('class', 'NoClass')}_{elem_w}x{elem_h}"
    content_desc = elem.get("content-desc", "")
    if content_desc and len(content_desc) < 25:
        sanitized_desc = "".join(e for e in content_desc if e.isalnum() or e in "_-").replace(" ", "_")
        uid += f"_{sanitized_desc}"
    role_hint = None
    text = elem.get("text", "").lower()
    elem_class = elem.get("class", "").lower()
    display_kws = ["display", "result", "formula"]
    search_space = f"{res_id.lower()} {content_desc.lower()} {text}"
    if any(kw in search_space for kw in ["search", "query", "find"]) or "searchview" in elem_class:
        role_hint = "search_bar"
    elif any(kw in search_space for kw in ["nav", "navigation", "tab", "toolbar", "home", "profile", "menu"]) or "bottomnavigation" in elem_class or "tabwidget" in elem_class:
        role_hint = "nav_item"
    elif any(kw in search_space for kw in display_kws):
        role_hint = "result_display"
    return uid, role_hint

def extract_interactive_elements(xml_path: str) -> List[UIElement]:
    if not xml_path or xml_path == "ERROR": return []
    interactive_elements = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        parent_map = {c: p for p in root.iter() for c in p}
        for elem in root.iter():
            if elem.get("clickable") == "true" or elem.get("focusable") == "true":
                bounds_str = elem.get("bounds")
                if not bounds_str: continue
                try:
                    coords = [int(c) for c in bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")]
                    bbox = ((coords[0], coords[1]), (coords[2], coords[3]))
                    if bbox[0][0] == bbox[1][0] or bbox[0][1] == bbox[1][1]: continue
                    
                    visible_text = elem.get("text", "")
                    if not visible_text:
                        visible_text = elem.get("content-desc", "")

                    uid, role_hint = _generate_element_uid(elem)
                    parent = parent_map.get(elem)
                    if parent is not None:
                        parent_uid, _ = _generate_element_uid(parent)
                        uid = f"{parent_uid}.{uid}"
                    
                    attributes = "clickable" if elem.get("clickable") == "true" else "focusable"
                    if role_hint: attributes += f",{role_hint}"
                    
                    # *** NEW: Add text to the UIElement object ***
                    interactive_elements.append(UIElement(uid=uid, bbox=bbox, attributes=attributes, text=visible_text))
                except (ValueError, IndexError): continue
    except ET.ParseError as e:
        log_message("ERROR", f"Failed to parse XML file at {xml_path}: {e}", component="UIParser", color="red")
        return []

    interactive_elements.sort(key=lambda e: (e.bbox[0][1], e.bbox[0][0]))
    
    final_elements = []
    min_dist = settings.get_setting("device.min_element_dist", 20)
    for elem in interactive_elements:
        is_too_close = False
        center_x, center_y = (elem.bbox[0][0] + elem.bbox[1][0]) // 2, (elem.bbox[0][1] + elem.bbox[1][1]) // 2
        for final_elem in final_elements:
            final_center_x, final_center_y = (final_elem.bbox[0][0] + final_elem.bbox[1][0]) // 2, (final_elem.bbox[0][1] + final_elem.bbox[1][1]) // 2
            if abs(center_x - final_center_x) + abs(center_y - final_center_y) < min_dist:
                is_too_close = True
                break
        if not is_too_close: final_elements.append(elem)
    return final_elements