
import sys
import os
import json

# Add parent dirs to sys path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger
from options import OPTIONS

def read_img_list(file_path):
    """Reads a list of parsed images from a given json file path."""
    with open(file_path, 'r', encoding='utf-8') as f:
        img_list = json.load(f)
    return img_list

def main():
    parsed_imgs_list_file_path = OPTIONS.output_dir / "Image.json"
    parsed_imgs = read_img_list(parsed_imgs_list_file_path)
    logger.info(f"Total parsed images: {len(parsed_imgs)}")
    logger.debug(f"Options.export_dir: {OPTIONS.export_dir}")

    num_passed = 0
    for img_path in parsed_imgs:
        export_img_path = OPTIONS.export_dir / img_path.removeprefix("/") #/WRFrontiers/Content/... -> export_dir/WRFrontiers/Content/...
        
        # The export img does not specify a file extension, so we need to find the actual file
        full_img_path = None
        for ext in [".png", ".jpg", ".jpeg", ".svg"]:
            candidate_path = export_img_path.with_suffix(ext)
            if candidate_path.exists():
                full_img_path = candidate_path
                break

        if not full_img_path:
            file_name = export_img_path.name
            file_dir = export_img_path.parent
            logger.warning(f"No image extensions found for asset {file_name} in export directory {file_dir}, skipping.")
            continue

        logger.debug(f"Processing image: {full_img_path}")
        num_passed += 1


    logger.info(f"Total images processed successfully: {num_passed}/{len(parsed_imgs)}")

if __name__ == "__main__":
    main()