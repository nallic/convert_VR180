import os
os.environ["OPENCV_IO_ENABLE_OPENEXR"]="1"
import cv2
import numpy as np
import argparse
import glob
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

def load_st_map(st_path):
    """Load the ST map from an EXR file."""
    st_map = cv2.imread(st_path, cv2.IMREAD_ANYCOLOR | cv2.IMREAD_ANYDEPTH)
    if st_map is None:
        raise FileNotFoundError(f"Could not load ST map from {st_path}")
    return st_map

def apply_st_map(image, st_map):
    """Apply the ST map to the image to create a new mapped image."""
    
    # Get input image dimensions
    input_h, input_w = image.shape[:2]
    
    # Get ST map dimensions (which should match the output dimensions)
    output_h, output_w = st_map.shape[:2]
    
    # Split ST map into separate channels
    s_map = (st_map[:, :, 2]) * (input_w - 1)  # Scale S to input image width
    t_map = (1 - st_map[:, :, 1]) * (input_h - 1)  # Scale T to input image height

    # Ensure s_map and t_map are in the correct format for remapping
    s_map = s_map.astype(np.float32)
    t_map = t_map.astype(np.float32)

    # Apply the remap using OpenCV
    mapped_image = cv2.remap(image, s_map, t_map, interpolation=cv2.INTER_LANCZOS4 , borderMode=cv2.BORDER_CONSTANT, borderValue=0)

    return mapped_image

def process_image(image_path, st_map, output_folder):
    """Load an image, apply ST mapping, and save the result with debug outputs."""
    
    # Load the input image with Pillow to ensure color space compatibility
    with Image.open(image_path) as img_pil:
        try:
            img_pil = img_pil.convert("RGB")  # Ensure it's in RGB mode for consistent colors
        except:
            return # Cant load this image

    # Convert to OpenCV format (BGR) for processing
    image = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
    # Apply ST mapping
    mapped_image = apply_st_map(image, st_map)

    # Convert mapped image to RGB format for final saving
    mapped_image_rgb = cv2.cvtColor(mapped_image, cv2.COLOR_BGR2RGB)
    mapped_image_pil = Image.fromarray(mapped_image_rgb)
    
    # Define the output path and save the final output image with quality 90 (without EXIF)
    output_path = os.path.join(output_folder, os.path.splitext(os.path.basename(image_path))[0] + ".jpg")
    mapped_image_pil.save(output_path, format="JPEG", quality=95)

def main(st_path, input_folder, output_folder):
    # Load ST map
    st_map = load_st_map(st_path)
    
    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Define the list of allowed extensions
    allowed_extensions = ('.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp')

    # Example: List only files in a directory (all files)
    files = [f for f in os.listdir(input_folder) 
             if os.path.isfile(os.path.join(input_folder, f)) and f.lower().endswith(allowed_extensions)]

    # Process each image in the input folder in parallel
    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = []
        for image_name in files:
            print(image_name)
            image_path = os.path.join(input_folder, image_name)
            futures.append(executor.submit(process_image, image_path, st_map, output_folder))

        for future in as_completed(futures):
            future.result()  # Wait for all futures to complete

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process images with an ST map.")
    parser.add_argument("--st", type=str, required=True, help="Path to the ST map in EXR format")
    parser.add_argument("--input_folder", type=str, required=True, help="Path to the folder containing input images")
    parser.add_argument("--output_folder", type=str, required=True, help="Path to the folder for saving output images")
    
    args = parser.parse_args()
    main(args.st, args.input_folder, args.output_folder)
