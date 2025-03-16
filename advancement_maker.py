import os
import json
import glob
from pathlib import Path

def process_recipe_file(file_path):
    try:
        # Load the JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if type field exists
        if 'type' not in data:
            print(f"Error: 'type' field missing in {file_path}")
            return
        
        # Display the type information
        print(f"\nProcessing file: {file_path}")
        print(f"Type: {data['type']}")
        
        # Get or set category
        if 'category' in data:
            current_category = data['category']
            print(f"Current category: {current_category}")
        else:
            current_category = None
            print("No current category")
        
        # Get or set group
        if 'group' in data:
            current_group = data['group']
            print(f"Current group: {current_group}")
        else:
            current_group = None
            print("No current group")
        
        # Ask for category if needed
        valid_categories = ['building', 'misc', 'redstone', 'equipment']
        category = input(f"Enter category {valid_categories} (press Enter to keep current): ")
        
        if category and category in valid_categories:
            data['category'] = category
        elif category and category not in valid_categories:
            print(f"Invalid category. Using {'current' if current_category else 'none'}")
        elif not category and current_category:
            category = current_category
        else:
            print("No category set")
        
        # Ask for group
        group = input("Enter group (press Enter to keep current): ")
        if group:
            data['group'] = group
        elif current_group:
            group = current_group
        else:
            print("No group set")
        
        # Save the modified recipe file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"Updated recipe file saved to {file_path}")
        
        # Now create the advancement file
        create_advancement_file(file_path, data)
        
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")

def create_advancement_file(recipe_file_path, recipe_data):
    # Ask for the required item input
    required_item = input("Enter the required item for the advancement: ")
    
    # Determine file name and folder
    file_name = os.path.basename(recipe_file_path)
    file_name_without_ext = os.path.splitext(file_name)[0]
    
    # Determine if we're in minecraft or betterr namespace
    folder_path = os.path.dirname(recipe_file_path)
    folder_name = os.path.basename(folder_path)
    
    namespace = "betterr"
    if "minecraft" in folder_path.lower():
        namespace = "minecraft"
    
    # Create the advancement data
    advancement_data = {
        "parent": "minecraft:recipes/root",
        "criteria": {
            f"has_{required_item}": {
                "conditions": {
                    "items": [
                        {
                            "items": required_item
                        }
                    ]
                },
                "trigger": "minecraft:inventory_changed"
            },
            "has_the_recipe": {
                "conditions": {
                    "recipe": f"{namespace}:{file_name_without_ext}"
                },
                "trigger": "minecraft:recipe_unlocked"
            }
        },
        "requirements": [
            [
                "has_the_recipe",
                f"has_{required_item}"
            ]
        ],
        "rewards": {
            "recipes": [
                f"{namespace}:{file_name_without_ext}"
            ]
        }
    }
    
    # Create the advancement file path
    advancement_dir = os.path.join("Better Recipes", "data", "betterr", "advancement", "recipes", namespace)
    os.makedirs(advancement_dir, exist_ok=True)
    
    advancement_file_path = os.path.join(advancement_dir, file_name)
    
    # Save the advancement file
    with open(advancement_file_path, 'w') as f:
        json.dump(advancement_data, f, indent=4)
    
    print(f"Created advancement file at {advancement_file_path}")

def main():
    # Ask for the directory containing recipe files
    recipe_dir = input("Enter the directory containing recipe JSON files: ")
    
    # Check if directory exists
    if not os.path.isdir(recipe_dir):
        print(f"Error: Directory {recipe_dir} not found")
        return
    
    # Process all JSON files in the directory
    json_files = glob.glob(os.path.join(recipe_dir, "*.json"))
    
    if not json_files:
        print(f"No JSON files found in {recipe_dir}")
        return
    
    print(f"Found {len(json_files)} JSON files to process")
    
    for file_path in json_files:
        process_recipe_file(file_path)

if __name__ == "__main__":
    main()