
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

def get_texture_list():
    parsed_imgs_list_file_path = os.path.join(OPTIONS.output_dir, "Image.json")
    parsed_imgs = read_img_list(parsed_imgs_list_file_path)
    logger.info(f"Total parsed images: {len(parsed_imgs)}")

    texture_paths = [] #includes the extension that will be located
    num_passed = 0
    for img_path in parsed_imgs:
        export_img_path = os.path.join(OPTIONS.export_dir, img_path.lstrip("/")) #/WRFrontiers/Content/... -> export_dir/WRFrontiers/Content/...
        
        # The export img does not specify a file extension, so we need to find the actual file
        full_img_path = None
        for ext in [".png", ".jpg", ".jpeg", ".svg"]:
            candidate_path = export_img_path + ext
            if os.path.exists(candidate_path):
                full_img_path = candidate_path
                break

        if not full_img_path:
            file_name = os.path.basename(export_img_path)
            file_dir = os.path.dirname(export_img_path)
            logger.debug(f"No image extensions found for asset {file_name} in export directory {file_dir}, skipping.")
            continue

        #logger.debug(f"Processing image: {full_img_path}")
        texture_paths.append(full_img_path)
        num_passed += 1

    logger.info(f"Total images processed successfully: {num_passed}/{len(parsed_imgs)}")

    return texture_paths

def copy_textures_to_output(texture_paths, output_dir):
    """Copies textures from EXPORT_DIR/path/to/icon.ext to TEXTURE_OUTPUT_DIR/path/to/icon.ext"""
    os.makedirs(output_dir, exist_ok=True)

    for texture_path in texture_paths:
        if not os.path.exists(texture_path):
            logger.warning(f"Texture file does not exist: {texture_path}, skipping.")
            continue

        relative_path = os.path.relpath(texture_path, OPTIONS.export_dir)
        dest_path = os.path.join(output_dir, relative_path)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(texture_path, 'rb') as src_file:
            with open(dest_path, 'wb') as dest_file:
                dest_file.write(src_file.read())
        #logger.debug(f"Copied texture to: {dest_path}")

    logger.info(f"All textures copied to {output_dir}")

def main():
    """Main function to process parsed images."""
    logger.info("Starting to process parsed images...")

    texture_paths = get_texture_list()
    logger.info(f"Copying {len(texture_paths)} textures to output directory...")

    copy_textures_to_output(texture_paths, OPTIONS.texture_output_dir)

if __name__ == "__main__":
    main()