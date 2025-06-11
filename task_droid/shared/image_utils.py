import base64
import cv2
import numpy as np

from .log_utils import log_message

def is_dark_mode(image_path: str, threshold: int = 100) -> bool:
    """
    Determines if an image is likely in dark mode by checking its average brightness.

    Args:
        image_path (str): Path to the image file.
        threshold (int): The brightness threshold (0-255). Below this value,
                         the image is considered to be in dark mode.

    Returns:
        bool: True if the image is likely in dark mode, False otherwise.
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return False # Default to light mode on error
        
        average_brightness = np.mean(img)
        log_message("DEBUG", f"Image average brightness: {average_brightness:.2f} (Threshold: {threshold})", component="ImageUtils")
        
        return average_brightness < threshold
    except Exception as e:
        log_message("WARNING", f"Could not determine dark mode for {image_path}: {e}", component="ImageUtils")
        return False # Default to light mode on error


def _add_text_background(
    img, text, position, font_scale, text_rgb, bg_rgb, font, thickness, padding, alpha
):
    """Internal helper to draw text with a semi-transparent background."""
    try:
        (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        top_left = (position[0] - padding, position[1] - text_h - padding)
        bottom_right = (position[0] + text_w + padding, position[1] + baseline + padding)

        top_left = (max(0, top_left[0]), max(0, top_left[1]))
        bottom_right = (min(img.shape[1], bottom_right[0]), min(img.shape[0], bottom_right[1]))

        if top_left[0] >= bottom_right[0] or top_left[1] >= bottom_right[1]:
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


def label_ui_elements(image_path: str, output_path: str, elements: list):
    """
    Draws numbered labels on UI elements in an image, using high-contrast colors.
    """
    try:
        img = cv2.imread(image_path)
        if img is None:
            log_message("ERROR", f"Could not read image at {image_path}", component="ImageUtils")
            return

        text_color = (255, 0, 255)
        bg_color = (0, 0, 0)
        font = cv2.FONT_HERSHEY_SIMPLEX
        
        # *** CHANGE: Increased font_scale for better visibility ***
        font_scale = 1.5
        
        thickness = 3 # Make it bold
        padding = 5
        alpha = 0.6

        for i, elem in enumerate(elements):
            label_text = str(i + 1)
            tl, br = elem.bbox
            center_x = (tl[0] + br[0]) // 2
            center_y = (tl[1] + br[1]) // 2
            
            (text_w, text_h), _ = cv2.getTextSize(label_text, font, font_scale, thickness)
            text_pos = (center_x - text_w // 2, center_y + text_h // 2)

            _add_text_background(
                img, label_text, text_pos, font_scale,
                text_color, bg_color, font, thickness, padding, alpha
            )

        cv2.imwrite(output_path, img)
        
    except Exception as e:
        log_message("ERROR", f"An error occurred in label_ui_elements: {e}", component="ImageUtils")

def encode_image_to_base64(image_path: str) -> str | None:
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        log_message("ERROR", f"Image file not found for encoding: {image_path}", component="ImageUtils")
        return None
    except Exception as e:
        log_message("ERROR", f"Failed to encode image {image_path}: {e}", component="ImageUtils")
        return None