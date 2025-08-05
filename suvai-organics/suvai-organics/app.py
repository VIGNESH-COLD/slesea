import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from openpyxl import Workbook, load_workbook
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['EXCEL_FILE'] = 'products.xlsx'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Create products Excel file if not exists
if not os.path.exists(app.config['EXCEL_FILE']):
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Name', 'Description', 'Price', 'Category', 'Image', 'Position'])
    wb.save(app.config['EXCEL_FILE'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_products():
    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active
    products = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row:  # Skip empty rows
            products.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': row[3],
                'category': row[4],
                'image': row[5],
                'position': row[6]
            })
    # Sort products by position
    products.sort(key=lambda x: x['position'])
    return products

def save_product(product):
    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active
    
    # Find existing product or create new
    if 'id' in product and product['id']:
        for idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
            if row[0].value == product['id']:
                row[1].value = product['name']
                row[2].value = product['description']
                row[3].value = product['price']
                row[4].value = product['category']
                row[5].value = product['image']
                row[6].value = product['position']
                break
    else:
        # New product - get next position
        last_position = max([row[6].value for row in ws.iter_rows(min_row=2) if row[6].value] or [0])
        product['position'] = last_position + 1
        
        # Add new row
        ws.append([
            str(uuid.uuid4()),
            product['name'],
            product['description'],
            product['price'],
            product['category'],
            product['image'],
            product['position']
        ])
    
    wb.save(app.config['EXCEL_FILE'])

def delete_product(product_id):
    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active
    
    for idx, row in enumerate(ws.iter_rows(min_row=2), start=2):
        if row[0].value == product_id:
            # Delete row
            ws.delete_rows(idx)
            break
    
    wb.save(app.config['EXCEL_FILE'])

def reorder_products(product_id, direction):
    products = get_products()
    current_index = next((i for i, p in enumerate(products) if p['id'] == product_id), None)
    
    if current_index is None:
        return
    
    # Determine swap index
    if direction == 'up' and current_index > 0:
        swap_index = current_index - 1
    elif direction == 'down' and current_index < len(products) - 1:
        swap_index = current_index + 1
    else:
        return
    
    # Swap positions
    current_position = products[current_index]['position']
    products[current_index]['position'] = products[swap_index]['position']
    products[swap_index]['position'] = current_position
    
    # Save changes
    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active
    for product in products:
        for row in ws.iter_rows(min_row=2):
            if row[0].value == product['id']:
                row[6].value = product['position']
                break
    wb.save(app.config['EXCEL_FILE'])

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/products')
def products():
    products = get_products()
    categories = sorted(set(p['category'] for p in products))
    return render_template('products.html', products=products, categories=categories)


@app.route('/admin/products', methods=['GET', 'POST'])
def manage_products():
    if request.method == 'POST':
        product = {
            'id': request.form.get('id'),
            'name': request.form['name'],
            'description': request.form['description'],
            'price': request.form['price'],
            'category': request.form['category'],
            'image': request.form.get('current_image', '')
        }
        
        # Handle file upload
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_filename))
                product['image'] = unique_filename
        
        save_product(product)
        return redirect(url_for('manage_products'))
    
    products = get_products()
    return render_template('products-upload.html', products=products)

@app.route('/admin/product/delete/<product_id>')
def delete_product_route(product_id):
    delete_product(product_id)
    return redirect(url_for('manage_products'))

@app.route('/admin/product/move/<direction>/<product_id>')
def move_product(direction, product_id):
    reorder_products(product_id, direction)
    return redirect(url_for('manage_products'))

# Serve static files
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    app.run(debug=True)