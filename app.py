import os
import json
import shutil
import hashlib
import tempfile
import io
import zipfile
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
app.secret_key = "your_secret_key"  # CHANGE THIS to a secure key!

# Set up rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["10 per minute"])
limiter.init_app(app)

def load_options():
    """
    Loads all JSON files from the 'options' folder and groups them by category.
    """
    options_by_category = {}
    options_folder = "options"
    if not os.path.exists(options_folder):
        return options_by_category
    for filename in os.listdir(options_folder):
        if filename.endswith('.json'):
            with open(os.path.join(options_folder, filename), 'r', encoding='utf-8') as f:
                option = json.load(f)
            # Save the filename as the option id
            option["id"] = filename
            category = option.get("category", "Uncategorized")
            if category not in options_by_category:
                options_by_category[category] = []
            options_by_category[category].append(option)
    return options_by_category

def copy_files(src_base, dest_base, recipe_file, category):
    """
    Copies recipe and advancement files from source to destination.
    """
    # Copy recipe file
    src_recipe = os.path.join(src_base, "recipe", f"{recipe_file}.json")
    dest_recipe = os.path.join(dest_base, "recipe", f"{recipe_file}.json")
    if os.path.exists(src_recipe):
        os.makedirs(os.path.dirname(dest_recipe), exist_ok=True)
        shutil.copy(src_recipe, dest_recipe)
    
    # Copy advancement file if it exists
    category = category.lower()  # Ensure category is lowercase
    src_advancement = os.path.join(src_base, "advancement", "info", category)
    dest_advancement = os.path.join(dest_base, "advancement", "info", category)
    if os.path.exists(src_advancement):
        os.makedirs(os.path.dirname(dest_advancement), exist_ok=True)
        if os.path.isdir(src_advancement):
            shutil.copytree(src_advancement, dest_advancement, dirs_exist_ok=True)
        else:
            shutil.copy(src_advancement, dest_advancement)

def get_category_image_path(category):
    """
    Returns the file path (relative to the static folder) for the category’s MC image.
    The convention is to use the lowercase category name with spaces replaced by underscores.
    For example, a category named "My Category" should have its image at "mc_images/my_category.png"
    """
    filename = category.lower().replace(" ", "_") + ".png"
    return f"mc_images/{filename}"

@app.route("/", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def index():
    imported_recipes = []
    options_by_category = load_options()
    
    # Build a mapping of category names to image file paths (for use in the template)
    category_images = {}
    for category in options_by_category:
        category_images[category] = get_category_image_path(category)
    
    if request.method == "POST":
        # Importing an existing datapack ZIP file
        if 'import_zip' in request.files and request.files['import_zip'].filename != "":
            import_file = request.files['import_zip']
            try:
                with zipfile.ZipFile(import_file, 'r') as z:
                    if "SELECTED_RECIPES.txt" in z.namelist():
                        with z.open("SELECTED_RECIPES.txt") as f:
                            content = f.read().decode("utf-8")
                            # Expect one recipe per line (using display_name for this example)
                            imported_recipes = [line.strip() for line in content.splitlines() if line.strip()]
                    else:
                        flash("The uploaded ZIP does not contain a SELECTED_RECIPES.txt file.")
            except Exception as e:
                flash(f"Error importing datapack: {str(e)}")
            return render_template("index.html", options_by_category=options_by_category,
                       imported_recipes=imported_recipes,
                       category_images=category_images)

        
        # Creating a datapack from selected options
        selected_ids = request.form.getlist("options")
        if not selected_ids:
            flash("No options selected!")
            return redirect(url_for("index"))
        
        # Filter out the options that were selected
        all_options = [opt for opts in options_by_category.values() for opt in opts]
        selected_options = [opt for opt in all_options if opt["id"] in selected_ids]
        
        try:
            with tempfile.TemporaryDirectory() as tmpdirname:
                output_path = os.path.join(tmpdirname, "output_datapack")
                template_path = os.path.join("output", "template")
                if not os.path.exists(template_path):
                    flash("Template folder not found!")
                    return redirect(url_for("index"))
                shutil.copytree(template_path, output_path, dirs_exist_ok=True)
                
                # Write SELECTED_RECIPES.txt with the display names
                selected_names = [opt['display_name'] for opt in selected_options]
                selected_recipes_file = os.path.join(output_path, 'SELECTED_RECIPES.txt')
                with open(selected_recipes_file, "w", encoding="utf-8") as f:
                    f.write('\n'.join(selected_names))
                
                # Copy recipes and advancements for each selected option
                for option in selected_options:
                    category = option.get("category", "Uncategorized")
                    for recipe in option.get('recipes', []):
                        # Handle betterr namespace
                        copy_files(
                            os.path.join("Better Recipes", "data", "betterr"),
                            os.path.join(output_path, "data", "betterr"),
                            recipe,
                            category
                        )
                        # Handle minecraft namespace
                        copy_files(
                            os.path.join("Better Recipes", "data", "minecraft"),
                            os.path.join(output_path, "data", "minecraft"),
                            recipe,
                            category
                        )
                
                # Generate ZIP filename based on a hash of the sorted names
                options_string = "_".join([name.strip().replace(" ", "_") for name in sorted(selected_names) if name.strip()])
                hash_id = hashlib.md5(options_string.encode()).hexdigest()[:8]
                zip_filename = f"Better Recipes_{hash_id} 1.21.4.zip"
                archive_base = os.path.splitext(os.path.join(tmpdirname, zip_filename))[0]
                zip_filepath = shutil.make_archive(archive_base, 'zip', output_path)
                
                # Read the ZIP file into memory
                with open(zip_filepath, 'rb') as f:
                    zip_data = io.BytesIO(f.read())
                zip_data.seek(0)
                
                return send_file(
                    zip_data,
                    as_attachment=True,
                    download_name=zip_filename,
                    mimetype="application/zip"
                )
        except Exception as e:
            flash(f"Error creating datapack: {str(e)}")
            return redirect(url_for("index"))
    
    # GET request
    return render_template("index.html", options_by_category=options_by_category,
                       imported_recipes=imported_recipes,
                       category_images=category_images)


if __name__ == "__main__":
    app.run(debug=True)