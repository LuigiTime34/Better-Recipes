import os
import json
import shutil
import hashlib
import tempfile
import io
import zipfile
import logging
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Set up logging
logging.basicConfig(
    filename='app.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s'
)

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Change this to a secure value

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["10 per minute"])
limiter.init_app(app)

# Get base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_options():
    """
    Loads all JSON files from the 'options' folder and groups them by category.
    A normalized_category field is added to standardize folder naming.
    """
    options_by_category = {}
    options_folder = os.path.join(BASE_DIR, "options")

    if not os.path.exists(options_folder):
        logging.warning(f"Options folder not found at: {options_folder}")
        return options_by_category

    for filename in os.listdir(options_folder):
        if filename.endswith('.json'):
            try:
                with open(os.path.join(options_folder, filename), 'r', encoding='utf-8') as f:
                    option = json.load(f)
                option["id"] = filename
                category = option.get("category", "Uncategorized")
                # Normalize category for folder naming (adjust if needed)
                option["normalized_category"] = category.lower().replace(" ", "_")
                if category not in options_by_category:
                    options_by_category[category] = []
                options_by_category[category].append(option)
            except Exception as e:
                logging.error(f"Error loading option file {filename}: {str(e)}")

    return options_by_category


def get_category_image_path(category):
    """
    Returns the file path for the category's MC image.
    """
    filename = category.lower().replace(" ", "_") + ".png"
    return f"mc_images/{filename}"


def advancement_references_selected(file_path, all_selected_recipes):
    """
    Returns True if the advancement JSON (at file_path) references any of the selected recipes.
    Expects criteria -> conditions -> recipe in the JSON.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if "criteria" in data:
            for criterion in data["criteria"].values():
                if (
                    isinstance(criterion, dict) and 
                    "conditions" in criterion and 
                    "recipe" in criterion["conditions"]
                ):
                    recipe_ref = criterion["conditions"]["recipe"]
                    if isinstance(recipe_ref, str):
                        # Extract just the recipe ID part without namespace
                        if ":" in recipe_ref:
                            recipe_id = recipe_ref.split(":", 1)[1]
                            logging.debug(f"Checking if recipe '{recipe_id}' is in selected recipes")
                            if recipe_id in all_selected_recipes:
                                return True
                        else:
                            # Handle case where there might not be a namespace
                            if recipe_ref in all_selected_recipes:
                                return True
                                
        # Add debug logging to see what's happening when no match is found
        logging.debug(f"No matching recipes found in {file_path}. Selected recipes: {all_selected_recipes}")
        return False
    except Exception as e:
        logging.warning(f"Error reading advancement file {file_path}: {str(e)}")
        return False


def create_datapack(output_path, selected_options):
    """
    Creates the datapack with selected recipes and filtered advancements.
    """
    better_recipes_path = os.path.join(BASE_DIR, "Better Recipes")
    output_template_path = os.path.join(BASE_DIR, "output", "template")

    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)

    # Verify the template directory exists
    if not os.path.exists(better_recipes_path):
        logging.error(f"Better Recipes directory not found at: {better_recipes_path}")
        raise FileNotFoundError(f"Better Recipes directory not found at: {better_recipes_path}")

    # Verify the output template directory exists
    if not os.path.exists(output_template_path):
        logging.warning(f"Output template directory not found at: {output_template_path}")
        # Continue execution, we'll handle missing files individually

    # Copy pack.mcmeta (or create default)
    pack_mcmeta_src = os.path.join(better_recipes_path, "pack.mcmeta")
    if os.path.exists(pack_mcmeta_src):
        shutil.copy2(pack_mcmeta_src, os.path.join(output_path, "pack.mcmeta"))
        logging.info(f"Copied pack.mcmeta from {pack_mcmeta_src}")
    else:
        default_mcmeta = {
            "pack": {
                "pack_format": 61,
                "description": "https://luigitime34.pythonanywhere.com/"
            }
        }
        with open(os.path.join(output_path, "pack.mcmeta"), 'w', encoding='utf-8') as f:
            json.dump(default_mcmeta, f, indent=4)
        logging.info("Created default pack.mcmeta")

    # Create necessary directories for each namespace
    for namespace in ['betterr', 'minecraft']:
        os.makedirs(os.path.join(output_path, "data", namespace, "recipe"), exist_ok=True)
        os.makedirs(os.path.join(output_path, "data", namespace, "advancement"), exist_ok=True)
        os.makedirs(os.path.join(output_path, "data", namespace, "advancement", "info"), exist_ok=True)
        os.makedirs(os.path.join(output_path, "data", namespace, "function"), exist_ok=True)
        os.makedirs(os.path.join(output_path, "data", namespace, "tags", "function"), exist_ok=True)

    # Write selected recipes to a file
    selected_names = [opt['display_name'] for opt in selected_options]
    with open(os.path.join(output_path, 'SELECTED_RECIPES.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(selected_names))

    logging.info(f"Selected options: {selected_options}")

    recipes_copied = 0
    advancements_copied = 0
    function_files_copied = 0

    # Gather all selected categories
    selected_categories = set()
    for option in selected_options:
        if 'normalized_category' in option:
            selected_categories.add(option['normalized_category'])
        elif 'category' in option:
            # Normalize category if normalized_category is not present
            category = option['category'].lower().replace(" ", "_")
            selected_categories.add(category)
    
    logging.info(f"Selected categories: {selected_categories}")

    # Collect all selected recipe IDs
    all_selected_recipes = set()
    for option in selected_options:
        for recipe in option.get('recipes', []):
            all_selected_recipes.add(recipe)
            # Also add without namespace
            if ":" in recipe:
                all_selected_recipes.add(recipe.split(":", 1)[1])
    
    logging.info(f"All selected recipes: {all_selected_recipes}")

    # Copy selected recipes from both namespaces
    for option in selected_options:
        for recipe in option.get('recipes', []):
            logging.info(f"Processing recipe: {recipe}")
            for namespace in ['betterr', 'minecraft']:
                recipe_src = os.path.join(better_recipes_path, "data", namespace, "recipe", f"{recipe}.json")
                recipe_dest = os.path.join(output_path, "data", namespace, "recipe", f"{recipe}.json")
                if os.path.exists(recipe_src):
                    os.makedirs(os.path.dirname(recipe_dest), exist_ok=True)
                    shutil.copy2(recipe_src, recipe_dest)
                    recipes_copied += 1
                    logging.info(f"Copied recipe: {recipe_src} to {recipe_dest}")
                else:
                    logging.warning(f"Recipe not found: {recipe_src}")

    # Copy advancements from output/template directory
    namespace = 'betterr'  # Only process betterr namespace
    
    # New path structure - looking in output/template directory
    adv_src_base = os.path.join(output_template_path, "data", namespace, "advancement")
    adv_dest_base = os.path.join(output_path, "data", namespace, "advancement")

    # Check if the source directory exists
    if not os.path.exists(adv_src_base):
        logging.error(f"Advancement directory not found at: {adv_src_base}")
    else:
        logging.info(f"Processing advancements from path: {adv_src_base}")
        
        # Create the advancement directory if it doesn't exist
        os.makedirs(adv_dest_base, exist_ok=True)
        
        
        # Clone advancements from info folder
        info_path = os.path.join(adv_src_base, "info")
        if os.path.exists(info_path) and os.path.isdir(info_path):
            dest_info_path = os.path.join(adv_dest_base, "info")
            os.makedirs(dest_info_path, exist_ok=True)
            logging.info(f"Copying info advancements from {info_path}")
            
            # First, copy root.json if it exists
            root_json_path = os.path.join(info_path, "root.json")
            if os.path.exists(root_json_path):
                shutil.copy2(root_json_path, os.path.join(dest_info_path, "root.json"))
                advancements_copied += 1
                logging.info("Copied root.json")
            
            # Copy JSON files that relate to each selected category
            for filename in os.listdir(info_path):
                file_path = os.path.join(info_path, filename)
                
                # Skip directories and non-JSON files at root level
                if os.path.isdir(file_path) or not filename.endswith('.json'):
                    continue
                    
                # Skip root.json (already handled)
                if filename == "root.json":
                    continue
                
                # Check if this JSON file relates to a selected category
                category_match = False
                for category in selected_categories:
                    if category in filename.lower():
                        category_match = True
                        break
                        
                if category_match:
                    dest_file = os.path.join(dest_info_path, filename)
                    shutil.copy2(file_path, dest_file)
                    advancements_copied += 1
                    logging.info(f"Copied category JSON: {filename}")
            
            # Use the original Better Recipes path for category folders
            original_info_path = os.path.join(better_recipes_path, "data", namespace, "advancement", "info")
            logging.info(f"Looking for category folders in: {original_info_path}")
            
            if os.path.exists(original_info_path) and os.path.isdir(original_info_path):
                # Process each selected category
                for category in selected_categories:
                    src_category_path = os.path.join(original_info_path, category)
                    
                    if os.path.exists(src_category_path) and os.path.isdir(src_category_path):
                        logging.info(f"Found category folder: {category}")
                        
                        # Create the category folder in destination
                        dest_category_path = os.path.join(dest_info_path, category)
                        os.makedirs(dest_category_path, exist_ok=True)
                        
                        # Get options for this category
                        category_options = []
                        for option in selected_options:
                            option_category = option.get('normalized_category', '').lower()
                            if option_category == category.lower():
                                # Get the option ID (filename without extension)
                                option_id = option.get('id', '').split('.')[0]
                                if option_id:
                                    category_options.append(option_id)
                        
                        logging.info(f"Selected options for {category}: {category_options}")
                        
                        # Check each file in the category folder
                        option_files_found = False
                        for option_file in os.listdir(src_category_path):
                            if not option_file.endswith('.json'):
                                continue
                                
                            option_id = option_file.split('.')[0]
                            
                            # Check if this option was selected
                            if option_id in category_options:
                                src_option_path = os.path.join(src_category_path, option_file)
                                dest_option_path = os.path.join(dest_category_path, option_file)
                                shutil.copy2(src_option_path, dest_option_path)
                                advancements_copied += 1
                                option_files_found = True
                                logging.info(f"Copied option file: {category}/{option_file}")
                        
                        if not option_files_found:
                            logging.warning(f"No matching option files found for category: {category}")
                    else:
                        logging.warning(f"Category folder not found: {src_category_path}")
            else:
                logging.warning(f"Original info directory not found: {original_info_path}")
        
        # Copy triggers advancements
        triggers_path = os.path.join(adv_src_base, "triggers")
        if os.path.exists(triggers_path) and os.path.isdir(triggers_path):
            dest_triggers_path = os.path.join(adv_dest_base, "triggers")
            os.makedirs(dest_triggers_path, exist_ok=True)
            logging.info(f"Copying triggers advancements from {triggers_path}")
            
            for root, _, files in os.walk(triggers_path):
                for file in files:
                    if file.endswith('.json'):
                        src_file = os.path.join(root, file)
                        rel_path = os.path.relpath(src_file, triggers_path)
                        dest_file = os.path.join(dest_triggers_path, rel_path)
                        
                        # Ensure the destination directory exists
                        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                        
                        # Copy the file
                        shutil.copy2(src_file, dest_file)
                        advancements_copied += 1
                        logging.info(f"Copied triggers advancement: {rel_path}")

        # Also check for other directories that might need to be copied
        for item in os.listdir(adv_src_base):
            item_path = os.path.join(adv_src_base, item)
            if os.path.isdir(item_path) and item not in ('info', 'triggers'):
                dest_item_path = os.path.join(adv_dest_base, item)
                os.makedirs(dest_item_path, exist_ok=True)
                logging.info(f"Copying advancements from {item_path}")
                
                for root, _, files in os.walk(item_path):
                    for file in files:
                        if file.endswith('.json'):
                            src_file = os.path.join(root, file)
                            rel_path = os.path.relpath(src_file, item_path)
                            dest_file = os.path.join(dest_item_path, rel_path)
                            
                            # Ensure the destination directory exists
                            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                            
                            # Copy the file
                            shutil.copy2(src_file, dest_file)
                            advancements_copied += 1
                            logging.info(f"Copied {item} advancement: {rel_path}")

    # Copy function files from output/template directory too
    functions_src = os.path.join(output_template_path, "data", "betterr", "function")
    functions_dest = os.path.join(output_path, "data", "betterr", "function")
    
    if os.path.exists(functions_src) and os.path.isdir(functions_src):
        os.makedirs(functions_dest, exist_ok=True)
        logging.info(f"Copying function files from {functions_src}")
        
        for root, _, files in os.walk(functions_src):
            for file in files:
                if file.endswith('.mcfunction'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, functions_src)
                    dest_file = os.path.join(functions_dest, rel_path)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(file_path, dest_file)
                    function_files_copied += 1
                    logging.info(f"Copied function file: {rel_path}")
    
    # Also try the original Better Recipes path for functions
    alt_functions_src = os.path.join(better_recipes_path, "data", "betterr", "function")
    if os.path.exists(alt_functions_src) and os.path.isdir(alt_functions_src):
        os.makedirs(functions_dest, exist_ok=True)
        logging.info(f"Copying function files from alternate path {alt_functions_src}")
        
        for root, _, files in os.walk(alt_functions_src):
            for file in files:
                if file.endswith('.mcfunction'):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, alt_functions_src)
                    dest_file = os.path.join(functions_dest, rel_path)
                    os.makedirs(os.path.dirname(dest_file), exist_ok=True)
                    shutil.copy2(file_path, dest_file)
                    function_files_copied += 1
                    logging.info(f"Copied function file from alternate path: {rel_path}")

    # Copy function tags for both namespaces
    for namespace in ['betterr', 'minecraft']:
        # Try output/template path first
        tags_src = os.path.join(output_template_path, "data", namespace, "tags", "function")
        tags_dest = os.path.join(output_path, "data", namespace, "tags", "function")
        
        if os.path.exists(tags_src) and os.path.isdir(tags_src):
            os.makedirs(tags_dest, exist_ok=True)
            logging.info(f"Copying function tags from {tags_src}")
            
            for file in os.listdir(tags_src):
                if file.endswith('.json'):
                    file_path = os.path.join(tags_src, file)
                    dest_file = os.path.join(tags_dest, file)
                    shutil.copy2(file_path, dest_file)
                    function_files_copied += 1
                    logging.info(f"Copied function tag: {file}")
        
        # Also try the original Better Recipes path
        alt_tags_src = os.path.join(better_recipes_path, "data", namespace, "tags", "function")
        if os.path.exists(alt_tags_src) and os.path.isdir(alt_tags_src):
            os.makedirs(tags_dest, exist_ok=True)
            logging.info(f"Copying function tags from alternate path {alt_tags_src}")
            
            for file in os.listdir(alt_tags_src):
                if file.endswith('.json'):
                    file_path = os.path.join(alt_tags_src, file)
                    dest_file = os.path.join(tags_dest, file)
                    shutil.copy2(file_path, dest_file)
                    function_files_copied += 1
                    logging.info(f"Copied function tag from alternate path: {file}")

    logging.info(f"Datapack creation completed. Copied {recipes_copied} recipes, {advancements_copied} advancements, and {function_files_copied} function files.")

    return {
        "recipes_copied": recipes_copied,
        "advancements_copied": advancements_copied,
        "function_files_copied": function_files_copied,
        "selected_options": len(selected_options)
    }

def create_zip_in_memory(directory_path):
    """
    Creates a ZIP file in memory from a directory.
    """
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory_path)
                logging.info(f"Adding to ZIP: {file_path} as {arcname}")
                zf.write(file_path, arcname)
    memory_file.seek(0)
    return memory_file


@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def index():
    try:
        imported_recipes = []
        options_by_category = load_options()
        category_images = {category: get_category_image_path(category) for category in options_by_category}

        if request.method == "POST":
            # Handle ZIP import
            if 'import_zip' in request.files and request.files['import_zip'].filename:
                import_file = request.files['import_zip']
                try:
                    with zipfile.ZipFile(import_file, 'r') as z:
                        if "SELECTED_RECIPES.txt" in z.namelist():
                            with z.open("SELECTED_RECIPES.txt") as f:
                                content = f.read().decode("utf-8")
                                imported_recipes = [line.strip() for line in content.splitlines() if line.strip()]
                        else:
                            flash("The uploaded ZIP does not contain a SELECTED_RECIPES.txt file.")
                except Exception as e:
                    logging.error(f"Error importing datapack: {str(e)}")
                    flash(f"Error importing datapack: {str(e)}")
                return render_template("index.html",
                                       options_by_category=options_by_category,
                                       imported_recipes=imported_recipes,
                                       category_images=category_images)

            # Handle datapack creation
            selected_ids = request.form.getlist("options")
            if not selected_ids:
                flash("No options selected!")
                return redirect(url_for("index"))

            # Get selected options from all loaded options
            all_options = [opt for opts in options_by_category.values() for opt in opts]
            selected_options = [opt for opt in all_options if opt["id"] in selected_ids]

            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    output_path = os.path.join(temp_dir, "datapack")
                    os.makedirs(output_path)
                    create_datapack(output_path, selected_options)

                    selected_names = [opt['display_name'] for opt in selected_options]
                    names_string = "".join(name.strip().replace(" ", "_") for name in sorted(selected_names))
                    hash_id = hashlib.md5(names_string.encode()).hexdigest()[:8]
                    zip_filename = f"Better_Recipes_{hash_id}_1.21.4.zip"

                    memory_file = create_zip_in_memory(output_path)

                    return send_file(
                        memory_file,
                        mimetype='application/zip',
                        as_attachment=True,
                        download_name=zip_filename
                    )

            except Exception as e:
                logging.error(f"Error creating datapack: {str(e)}")
                flash(f"Error creating datapack: {str(e)}")
                return redirect(url_for("index"))

        return render_template("index.html",
                               options_by_category=options_by_category,
                               imported_recipes=imported_recipes,
                               category_images=category_images)

    except Exception as e:
        logging.error(f"Unhandled error in index route: {str(e)}")
        flash("An unexpected error occurred. Please try again later.")
        return render_template("index.html",
                               options_by_category={},
                               imported_recipes=[],
                               category_images={})


if __name__ == "__main__":
    app.run(debug=False)
