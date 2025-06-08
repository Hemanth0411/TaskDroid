import base64
import cv2
import numpy as np

from .log_utils import log_message

def _add_text_background(
    img, text, position, font_scale, text_rgb, bg_rgb, font, thickness, padding, alpha
):
    """Internal helper to draw text with a semi-transparent background."""
    try:
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Position is the top-left corner of the text itself
        # We calculate the background box from there
        top_left = (position[0] - padding, position[1] - text_h - padding)
        bottom_right = (position[0] + text_w + padding, position[1] + baseline + padding)

        # Ensure coordinates are within image bounds
        top_left = (max(0, top_left[0]), max(0, top_left[1]))
        bottom_right = (min(img.shape[1], bottom_right[0]), min(img.shape[0], bottom_right[1]))

        if top_left[0] >= bottom_right[0] or top_left[1] >= bottom_right[1]:
            # If the box is invalid, just draw the text without a background
            cv2.putText(img, text, position, font, font_scale, text_rgb, thickness, cv2.LINE_AA)
            return img

        sub_img = img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]
        
        bg_rect = np.full(sub_img.shape, bg_rgb, dtype=np.uint8)
        
        res = cv2.addWeighted(sub_img, alpha, bg_rect, 1 - alpha, 1.0)
        
        img[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]] = res
        
        cv2.putText(img, text, position, font, font_scale, text_rgb, thickness, cv2.LINE_AA)
        return img
    except Exception as e:
        log_message("ERROR", f"Failed to draw text with background for '{text}': {e}", component="ImageUtils")
        return img


def label_ui_elements(image_path: str, output_path: str, elements: list, dark_mode: bool = False):
    """
    Draws numbered labels on UI elements in an image.

    The label is placed at the center of the element's bounding box.

    Args:
        image_path (str): Path to the source image.
        output_path (str): Path to save the labeled image.
        elements (list): A list of UIElement objects, each with a 'bbox' attribute.
        dark_mode (bool): If true, use light text on dark background. Defaults to False.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            log_message("ERROR", f"Could not read image at {image_path}", component="ImageUtils")
            return

        # Define colors and style based on mode
        text_color = (255, 255, 255) if dark_mode else (0, 0, 0) # White or Black
        bg_color = (50, 50, 50) if dark_mode else (220, 220, 220) # Dark or Light Gray
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        padding = 5
        alpha = 0.7 # Opacity of the background

        for i, elem in enumerate(elements):
            label_text = str(i + 1)
            
            # Bbox is ((x1, y1), (x2, y2))
            tl, br = elem.bbox
            
            # Calculate the center of the bounding box
            center_x = (tl[0] + br[0]) // 2
            center_y = (tl[1] + br[1]) // 2
            
            # Estimate text size to center the label
            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
            
            # Calculate top-left position for the text so it's centered
            text_pos = (center_x - text_w // 2, center_y + text_h // 2)

            _add_text_background(
                img, label_text, text_pos, font_scale,
                text_color, bg_color, font, thickness, padding, alpha
            )

        cv2.imwrite(output_path, img)
        
    except Exception as e:
        log_message("ERROR", f"An error occurred in label_ui_elements: {e}", component="ImageUtils")


def encode_image_to_base64(image_path: str) -> str | None:
    """
    Encodes an image file to a base64 string.

    Args:
        image_path (str): The path to the image file.

    Returns:
        str | None: The base64 encoded string, or None if an error occurs.
    """
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        log_message("ERROR", f"Image file not found for encoding: {image_path}", component="ImageUtils")
        return None
    except Exception as e:
        log_message("ERROR", f"Failed to encode image {image_path}: {e}", component="ImageUtils")
        return None