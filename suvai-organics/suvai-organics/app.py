import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
from openpyxl import Workbook, load_workbook
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# ---------------------------- Admin Login ----------------------------
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'Admin@suvai_organics' and password == 'suvai_1209':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password')

    return render_template('admin-login.html')

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('admin-dashboard.html')

# ---------------------------- Config ----------------------------
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['EXCEL_FILE'] = 'products.xlsx'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if not os.path.exists(app.config['EXCEL_FILE']):
    wb = Workbook()
    ws = wb.active
    ws.append(['ID', 'Name', 'Description', 'Price', 'Category', 'Image', 'Position'])
    wb.save(app.config['EXCEL_FILE'])

# ---------------------------- Helpers ----------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_products():
    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active
    products = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row:
            products.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'price': row[3],
                'category': row[4],
                'image': row[5],
                'position': row[6]
            })
    products.sort(key=lambda x: x['position'])
    return products

def save_product(product):
    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active

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
        last_position = max([row[6].value for row in ws.iter_rows(min_row=2) if row[6].value] or [0])
        product['position'] = last_position + 1
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
            ws.delete_rows(idx)
            break

    wb.save(app.config['EXCEL_FILE'])

def reorder_products(product_id, direction):
    products = get_products()
    current_index = next((i for i, p in enumerate(products) if p['id'] == product_id), None)

    if current_index is None:
        return

    if direction == 'up' and current_index > 0:
        swap_index = current_index - 1
    elif direction == 'down' and current_index < len(products) - 1:
        swap_index = current_index + 1
    else:
        return

    current_position = products[current_index]['position']
    products[current_index]['position'] = products[swap_index]['position']
    products[swap_index]['position'] = current_position

    wb = load_workbook(app.config['EXCEL_FILE'])
    ws = wb.active
    for product in products:
        for row in ws.iter_rows(min_row=2):
            if row[0].value == product['id']:
                row[6].value = product['position']
                break
    wb.save(app.config['EXCEL_FILE'])

# ---------------------------- Public Routes ----------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/natural-farming')
def natural_farming():
    return render_template('natural-farming.html')

@app.route('/farmers')
def farmers():
    return render_template('farmers.html')

@app.route('/partners')
def partners():
    return render_template('partners.html')

@app.route('/register')
def register():
    return render_template('registration.html')

@app.route('/products')
def products():
    products = get_products()
    categories = sorted(set(p['category'] for p in products))
    return render_template('products.html', products=products, categories=categories)

# ---------------------------- Admin Routes ----------------------------
@app.route('/admin/products', methods=['GET', 'POST'])
def manage_products():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        product = {
            'id': request.form.get('id'),
            'name': request.form['name'],
            'description': request.form['description'],
            'price': request.form['price'],
            'category': request.form['category'],
            'image': request.form.get('current_image', '')
        }

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
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    delete_product(product_id)
    return redirect(url_for('manage_products'))

@app.route('/admin/product/move/<direction>/<product_id>')
def move_product(direction, product_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    reorder_products(product_id, direction)
    return redirect(url_for('manage_products'))

# ---------------------------- Static Catch-all ----------------------------
@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

if __name__ == '__main__':
    # Use host='0.0.0.0' and disable reloader to avoid issues in limited environments
    app.run(debug=True, host='0.0.0.0', use_reloader=False)
