import os
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("file_renamer.log"),
        logging.StreamHandler()
    ]
)

def rename_files():
    # Define paths
    options_folder = "options"
    info_base_path = os.path.join("Better Recipes", "data", "betterr", "advancement", "info")
    
    # Check if folders exist
    if not os.path.exists(options_folder):
        logging.error(f"Options folder '{options_folder}' not found!")
        return
        
    if not os.path.exists(info_base_path):
        logging.error(f"Info base path '{info_base_path}' not found!")
        return
    
    # Track statistics
    total_files = 0
    successful_renames = 0
    failed_renames = 0
    
    # Process each JSON file in the options folder
    for filename in os.listdir(options_folder):
        if not filename.endswith('.json'):
            continue
            
        total_files += 1
        options_file_path = os.path.join(options_folder, filename)
        
        try:
            # Load the JSON file
            with open(options_file_path, 'r') as f:
                data = json.load(f)
            
            # Extract category and display_name
            if 'category' not in data or 'display_name' not in data:
                logging.warning(f"File {filename} missing required keys (category or display_name).")
                failed_renames += 1
                continue
                
            category = data['category']
            display_name = data['display_name']
            
            # Convert category to lowercase for case-insensitive comparison
            category_lower = category.lower()
            
            # Find the category folder (case-insensitive)
            category_folder = None
            for folder in os.listdir(info_base_path):
                if folder.lower() == category_lower:
                    category_folder = os.path.join(info_base_path, folder)
                    break
            
            if not category_folder or not os.path.exists(category_folder):
                logging.warning(f"Category folder '{category}' not found for file {filename}.")
                failed_renames += 1
                continue
            
            # Transform display_name to expected filename format
            # Replace spaces with underscores and convert to lowercase
            expected_filename_base = display_name.lower().replace(' ', '_')
            
            # Find the corresponding file in the category folder
            found = False
            for info_filename in os.listdir(category_folder):
                # Get the base name without extension
                info_file_base = os.path.splitext(info_filename)[0].lower()
                
                # Check for exact match
                if info_file_base == expected_filename_base:
                    # Found a match! Rename the file
                    old_path = os.path.join(category_folder, info_filename)
                    new_filename = os.path.splitext(filename)[0] + os.path.splitext(info_filename)[1]
                    new_path = os.path.join(category_folder, new_filename)
                    
                    os.rename(old_path, new_path)
                    logging.info(f"SUCCESS: Renamed '{old_path}' to '{new_path}'")
                    found = True
                    successful_renames += 1
                    break
            
            if not found:
                logging.warning(f"No matching file found for {filename} with display_name '{display_name}' (expected: '{expected_filename_base}.json') in category '{category}'.")
                failed_renames += 1
                
        except json.JSONDecodeError:
            logging.error(f"Error parsing JSON file: {filename}")
            failed_renames += 1
        except Exception as e:
            logging.error(f"Error processing file {filename}: {str(e)}")
            failed_renames += 1

    # Log summary
    logging.info(f"Summary: Processed {total_files} files - {successful_renames} successful renames, {failed_renames} failed")

if __name__ == "__main__":
    logging.info("Starting file renaming process...")
    rename_files()
    logging.info("File renaming process completed.")