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
    
    # Create necessary directories
    os.makedirs(os.path.join(output_path, "data", "betterr", "recipes"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "data", "minecraft", "recipes"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "data", "betterr", "advancements"), exist_ok=True)
    os.makedirs(os.path.join(output_path, "data", "minecraft", "advancements"), exist_ok=True)

    # Write selected recipes to file
    selected_names = [opt['display_name'] for opt in selected_options]
    with open(os.path.join(output_path, 'SELECTED_RECIPES.txt'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(selected_names))

    # Copy recipes and advancements
    for option in selected_options:
        category = option.get("category", "Uncategorized").lower()
        
        for recipe in option.get('recipes', []):
            # Handle betterr namespace
            for namespace in ['betterr', 'minecraft']:
                recipe_src = os.path.join(better_recipes_path, "data", namespace, "recipes", f"{recipe}.json")
                recipe_dest = os.path.join(output_path, "data", namespace, "recipes", f"{recipe}.json")
                
                if os.path.exists(recipe_src):
                    os.makedirs(os.path.dirname(recipe_dest), exist_ok=True)
                    shutil.copy2(recipe_src, recipe_dest)

                # Copy advancements if they exist
                adv_src = os.path.join(better_recipes_path, "data", namespace, "advancements", "info", category)
                adv_dest = os.path.join(output_path, "data", namespace, "advancements", "info", category)
                
                if os.path.exists(adv_src):
                    if os.path.isdir(adv_src):
                        shutil.copytree(adv_src, adv_dest, dirs_exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(adv_dest), exist_ok=True)
                        shutil.copy2(adv_src, adv_dest)

def create_zip_in_memory(directory_path):
    """
    Creates a ZIP file in memory from a directory.
    """
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, directory_path)
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