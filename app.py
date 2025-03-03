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

def create_datapack(output_path, selected_options):
    """
    Creates the datapack with selected recipes and advancements.
    """
    better_recipes_path = os.path.join(BASE_DIR, "Better Recipes")
    
    # Ensure the output directory exists
    os.makedirs(output_path, exist_ok=True)
    
    # First, check if the Better Recipes directory exists
    if not os.path.exists(better_recipes_path):
        logging.error(f"Better Recipes directory not found at: {better_recipes_path}")
        raise FileNotFoundError(f"Better Recipes directory not found at: {better_recipes_path}")
    
    # Copy pack.mcmeta file
    pack_mcmeta_src = os.path.join(better_recipes_path, "pack.mcmeta")
    if os.path.exists(pack_mcmeta_src):
        shutil.copy2(pack_mcmeta_src, os.path.join(output_path, "pack.mcmeta"))
        logging.info(f"Copied pack.mcmeta from {pack_mcmeta_src}")
    else:
        # Create a default pack.mcmeta
        default_mcmeta = {
            "pack": {
                "pack_format": 61,
                "description": "https://luigitime34.pythonanywhere.com/"
            }
        }
        with open(os.path.join(output_path, "pack.mcmeta"), 'w', encoding='utf-8') as f:
            json.dump(default_mcmeta, f, indent=4)
        logging.info("Created default pack.mcmeta")
    
    # Create necessary directories
    for namespace in ['betterr', 'minecraft']:
        os.makedirs(os.path.join(output_path, "data", namespace, "recipe"), exist_ok=True)
        os.makedirs(os.path.join(output_path, "data", namespace, "advancement", "info"), exist_ok=True)
    
    # Write selected recipes to file
    selected_names = [opt['display_name'] for opt in selected_options]
    with open(os.path.join(output_path, 'SELECTED_RECIPES.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(selected_names))
    
    # Log the selected options
    logging.info(f"Selected options: {selected_options}")
    
    # Copy recipes and advancements
    recipes_copied = 0
    advancements_copied = 0
    
    # Collect all selected recipe IDs and categories
    all_selected_recipes = []
    selected_categories = set()
    for option in selected_options:
        all_selected_recipes.extend(option.get('recipes', []))
        selected_categories.add(option.get("category", "Uncategorized").lower())
    
    # First, copy all selected recipes
    for option in selected_options:
        for recipe in option.get('recipes', []):
            logging.info(f"Processing recipe: {recipe}")
            
            # Handle both namespaces
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
    
    # Now, copy necessary advancement files and folders
    for category in selected_categories:
        logging.info(f"Processing advancements for category: {category}")
        
        for namespace in ['betterr', 'minecraft']:
            # Copy root.json if it exists
            root_adv_paths = [
                os.path.join(better_recipes_path, "data", namespace, "advancement", "root.json"),
                os.path.join(better_recipes_path, "data", namespace, "advancement", "info", "root.json")
            ]
            
            for root_path in root_adv_paths:
                if os.path.exists(root_path):
                    rel_path = os.path.relpath(root_path, os.path.join(better_recipes_path, "data", namespace, "advancement"))
                    dest_path = os.path.join(output_path, "data", namespace, "advancement", rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(root_path, dest_path)
                    advancements_copied += 1
                    logging.info(f"Copied root advancement: {root_path} to {dest_path}")
            
            # Check for both category advancement files and directories
            # 1. Category-specific JSON file
            category_file_paths = [
                os.path.join(better_recipes_path, "data", namespace, "advancement", f"{category}.json"),
                os.path.join(better_recipes_path, "data", namespace, "advancement", "info", f"{category}.json")
            ]
            
            for cat_path in category_file_paths:
                if os.path.exists(cat_path):
                    rel_path = os.path.relpath(cat_path, os.path.join(better_recipes_path, "data", namespace, "advancement"))
                    dest_path = os.path.join(output_path, "data", namespace, "advancement", rel_path)
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    shutil.copy2(cat_path, dest_path)
                    advancements_copied += 1
                    logging.info(f"Copied category advancement file: {cat_path} to {dest_path}")
            
            # 2. Category-specific directories
            category_dir_paths = [
                os.path.join(better_recipes_path, "data", namespace, "advancement", category),
                os.path.join(better_recipes_path, "data", namespace, "advancement", "info", category)
            ]
            
            for cat_dir in category_dir_paths:
                if os.path.exists(cat_dir) and os.path.isdir(cat_dir):
                    # Instead of copying the whole directory, copy only advancement files
                    # that correspond to selected recipes
                    for root, _, files in os.walk(cat_dir):
                        for file in files:
                            if file.endswith('.json'):
                                file_base = os.path.splitext(file)[0]
                                file_path = os.path.join(root, file)
                                
                                # Check if this file matches a recipe ID or is critical to the advancement tree
                                should_copy = False
                                
                                # Copy if filename matches a recipe ID
                                if file_base in all_selected_recipes:
                                    should_copy = True
                                    logging.info(f"Advancement file {file} matches recipe ID {file_base}")
                                
                                # Copy if it appears to be an important category file
                                elif file_base in ["root", category, f"{category}_root"]:
                                    should_copy = True
                                    logging.info(f"Copying essential category advancement file: {file}")
                                
                                # Otherwise, check if its content references any of our recipes
                                else:
                                    try:
                                        with open(file_path, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                            
                                        for recipe_id in all_selected_recipes:
                                            if recipe_id in content:
                                                should_copy = True
                                                logging.info(f"Advancement file {file} references recipe {recipe_id}")
                                                break
                                    except Exception as e:
                                        logging.warning(f"Error reading advancement file {file}: {str(e)}")
                                
                                if should_copy:
                                    rel_path = os.path.relpath(file_path, os.path.join(better_recipes_path, "data", namespace, "advancement"))
                                    dest_path = os.path.join(output_path, "data", namespace, "advancement", rel_path)
                                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                                    shutil.copy2(file_path, dest_path)
                                    advancements_copied += 1
                                    logging.info(f"Copied advancement file: {file_path} to {dest_path}")
    
    logging.info(f"Datapack creation completed. Copied {recipes_copied} recipes and {advancements_copied} advancements.")
    
    # Return information about what was copied
    return {
        "recipes_copied": recipes_copied,
        "advancements_copied": advancements_copied,
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

            # Get selected options
            all_options = [opt for opts in options_by_category.values() for opt in opts]
            selected_options = [opt for opt in all_options if opt["id"] in selected_ids]

            try:
                with tempfile.TemporaryDirectory() as temp_dir:
                    # Create datapack directory
                    output_path = os.path.join(temp_dir, "datapack")
                    os.makedirs(output_path)

                    # Create the datapack
                    create_datapack(output_path, selected_options)

                    # Generate unique filename
                    selected_names = [opt['display_name'] for opt in selected_options]
                    names_string = "".join(name.strip().replace(" ", "_") for name in sorted(selected_names))
                    hash_id = hashlib.md5(names_string.encode()).hexdigest()[:8]
                    zip_filename = f"Better_Recipes_{hash_id}_1.21.4.zip"

                    # Create ZIP in memory
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