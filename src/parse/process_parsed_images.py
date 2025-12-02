
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
    parsed_imgs_list_file_path = OPTIONS.output_dir / "Image.json"
    parsed_imgs = read_img_list(parsed_imgs_list_file_path)
    logger.info(f"Total parsed images: {len(parsed_imgs)}")

    texture_paths = [] #includes the extension that will be located
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
        texture_paths.append(full_img_path)
        num_passed += 1

    logger.info(f"Total images processed successfully: {num_passed}/{len(parsed_imgs)}")

    return texture_paths

def copy_textures_to_output(texture_paths, output_dir):
    """Copies textures from EXPORT_DIR/path/to/icon.ext to TEXTURE_OUTPUT_DIR/path/to/icon.ext"""
    os.makedirs(output_dir, exist_ok=True)

    for texture_path in texture_paths:
        if not texture_path.exists():
            logger.warning(f"Texture file does not exist: {texture_path}, skipping.")
            continue

        relative_path = texture_path.relative_to(OPTIONS.export_dir)
        dest_path = output_dir / relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(texture_path, 'rb') as src_file:
            with open(dest_path, 'wb') as dest_file:
                dest_file.write(src_file.read())
        logger.debug(f"Copied texture to: {dest_path}")

    logger.info(f"All textures copied to {output_dir}")

def main():
    """Main function to process parsed images."""
    texture_paths = get_texture_list()

    copy_textures_to_output(texture_paths, OPTIONS.texture_output_dir)

if __name__ == "__main__":
    main()