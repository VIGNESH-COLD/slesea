import os
import uuid
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename

# ---------------------------- Config ----------------------------
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')  # Use env var in production

# Database Config - MySQL or SQLite
# For MySQL: set MYSQL_URI environment variable like:
# mysql+pymysql://username:password@localhost/suvai_organics
basedir = os.path.abspath(os.path.dirname(__file__))

MYSQL_URI = os.environ.get('MYSQL_URI')
if MYSQL_URI:
    app.config['SQLALCHEMY_DATABASE_URI'] = MYSQL_URI
    print("✓ Using MySQL Database")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data', 'suvai.db')
    print("✓ Using SQLite Database (set MYSQL_URI for MySQL)")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File Upload Config
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['GALLERY_FOLDER'] = 'static/uploads/gallery'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['GALLERY_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(basedir, 'data'), exist_ok=True)

# Extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'customer_login'
login_manager.login_message_category = 'info'

# ---------------------------- Models ----------------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='customer')  # 'admin' or 'customer'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    stock = db.Column(db.Integer, default=0)
    image_filename = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    customer_name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    city = db.Column(db.String(100), nullable=False)
    pin_code = db.Column(db.String(20), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    
    product = db.relationship('Product')

class GalleryItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    caption = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), default='Uncategorized')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Farmer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    crops = db.Column(db.String(200), nullable=True) # Comma separated
    status = db.Column(db.String(20), default='pending') # pending, approved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Partner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(150), nullable=False)
    contact_person = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    type = db.Column(db.String(50), nullable=True) # Retailer, Distributor, etc.
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ContactQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='reset_tokens')

# ---------------------------- Helpers ----------------------------

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def create_admin():
    # Helper to check/create admin
    with app.app_context():
        # db.create_all() # Ensure tables exist
        admin = User.query.filter_by(username='Admin@suvai_organics').first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash('suvai_1209').decode('utf-8')
            new_admin = User(username='Admin@suvai_organics', email='admin@suvai.com', password=hashed_pw, role='admin')
            db.session.add(new_admin)
            db.session.commit()
            print("Admin account created.")

# ---------------------------- Public Routes ----------------------------

@app.route('/')
def home():
    # Fetch random or latest products as 'featured'
    featured_products = Product.query.order_by(Product.created_at.desc()).limit(3).all()
    return render_template('index.html', featured_products=featured_products)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        if name and email and message:
            new_query = ContactQuery(name=name, email=email, message=message)
            db.session.add(new_query)
            db.session.commit()
            flash('Your message has been sent!', 'success')
            return redirect(url_for('contact'))
        else:
            flash('Please fill in all fields.', 'error')
            
    return render_template('contact.html')

@app.route('/gallery')
def gallery():
    gallery_items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    categories = sorted(set(item.category for item in gallery_items if item.category))
    return render_template('gallery.html', gallery_items=gallery_items, categories=categories)

@app.route('/natural-farming')
def natural_farming():
    return render_template('natural-farming.html')

@app.route('/farmers')
def farmers():
    approved_farmers = Farmer.query.filter_by(status='approved').all()
    return render_template('farmers.html', farmers=approved_farmers)

@app.route('/partners')
def partners():
    approved_partners = Partner.query.filter_by(status='approved').all()
    return render_template('partners.html', partners=approved_partners)

@app.route('/products')
def products():
    search_query = request.args.get('q', '')
    if search_query:
        products = Product.query.filter(Product.name.ilike(f'%{search_query}%')).all()
    else:
        products = Product.query.all()
    categories = sorted(set(p.category for p in products if p.category))
    return render_template('products.html', products=products, search_query=search_query, categories=categories)

# ---------------------------- Cart Routes ----------------------------

@app.route('/cart')
def view_cart():
    if 'cart' not in session:
        session['cart'] = []
    
    # Calculate totals
    cart_items = session['cart']
    total_price = sum(item['price'] * item['quantity'] for item in cart_items)
    return render_template('cart.html', cart_items=cart_items, total=total_price)

@app.route('/add-to-cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    
    if 'cart' not in session:
        session['cart'] = []
    
    cart = session['cart']
    
    # Check if item already in cart
    found = False
    for item in cart:
        if item['id'] == product.id:
            item['quantity'] += 1
            found = True
            break
            
    if not found:
        cart.append({
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image': product.image_filename,
            'quantity': 1
        })
    
    session.modified = True
    flash(f'{product.name} added to cart!', 'success')
    return redirect(url_for('products'))

@app.route('/remove-from-cart/<int:product_id>')
def remove_from_cart(product_id):
    if 'cart' in session:
        session['cart'] = [item for item in session['cart'] if item['id'] != product_id]
        session.modified = True
        flash('Item removed from cart', 'success')
    return redirect(url_for('view_cart'))

@app.route('/update-cart/<int:product_id>/<action>')
def update_cart(product_id, action):
    if 'cart' in session:
        for item in session['cart']:
            if item['id'] == product_id:
                if action == 'increase':
                    item['quantity'] += 1
                elif action == 'decrease':
                    item['quantity'] -= 1
                    if item['quantity'] < 1:
                        session['cart'] = [i for i in session['cart'] if i['id'] != product_id]
                break
        session.modified = True
    return redirect(url_for('view_cart'))

# ---------------------------- User Routes ----------------------------

@app.route('/profile')
@login_required
def profile():
    # Fetch user's orders
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('user-profile.html', user=current_user, orders=orders)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'cart' not in session or not session['cart']:
        flash('Your cart is empty', 'error')
        return redirect(url_for('products'))
        
    total_price = sum(item['price'] * item['quantity'] for item in session['cart'])
    
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        phone = request.form.get('phone')
        shipping_address = request.form.get('shipping_address')
        city = request.form.get('city')
        pin_code = request.form.get('pin_code')
        payment_method = request.form.get('payment_method')
        notes = request.form.get('notes')
        
        user_id = current_user.id if current_user.is_authenticated else None
        
        new_order = Order(
            user_id=user_id,
            customer_name=full_name,
            phone=phone,
            shipping_address=shipping_address,
            city=city,
            pin_code=pin_code,
            payment_method=payment_method,
            total_amount=total_price,
            notes=notes
        )
        db.session.add(new_order)
        db.session.commit()
        
        for item in session['cart']:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item['id'],
                quantity=item['quantity'],
                price=item['price']
            )
            db.session.add(order_item)
            
        db.session.commit()
        
        session.pop('cart', None)
        session.modified = True
        
        if user_id:
             session['customer_name'] = full_name
             
        flash('Order placed successfully! Thank you for shopping with Suvai Organics.', 'success')
        return redirect(url_for('order_confirmation', order_id=new_order.id))
        
    return render_template('checkout.html', cart_items=session['cart'], total=total_price)

@app.route('/order-confirmation/<int:order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('order-confirmation.html', order=order)

@app.route('/orders-manage')
@login_required
def orders_manage():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('orders-manage.html', orders=orders)

@app.route('/admin/update-order-status/<int:order_id>', methods=['POST'])
@login_required
def update_order_status(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    status = request.form.get('status')
    order = Order.query.get_or_404(order_id)
    order.status = status
    db.session.commit()
    flash('Order status updated', 'success')
    return redirect(url_for('admin_order_details', order_id=order.id))

@app.route('/admin')
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        flash('Access denied. Admin only.', 'error')
        return redirect(url_for('home'))
    
    # Gather stats from database
    stats = {
        'product_count': Product.query.count(),
        'farmer_count': Farmer.query.filter_by(status='approved').count(),
        'pending_farmers': Farmer.query.filter_by(status='pending').count(),
        'pending_partners': Partner.query.filter_by(status='pending').count(),
        'pending_orders': Order.query.filter_by(status='pending').count(),
        'completed_orders': Order.query.filter_by(status='delivered').count(),
        'total_revenue': db.session.query(db.func.sum(Order.total_amount)).filter(Order.status == 'delivered').scalar() or 0
    }
    
    # Recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin-dashboard.html', stats=stats, recent_orders=recent_orders)

@app.route('/admin/order/<int:order_id>')
@login_required
def admin_order_details(order_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    order = Order.query.get_or_404(order_id)
    return render_template('admin-order-details.html', order=order)

# ---------------------------- Auth Routes ----------------------------

@app.route('/login', methods=['GET', 'POST'])
def customer_login():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('home'))

    if request.method == 'POST':
        email_or_username = request.form.get('username') # Form field might be 'username'
        password = request.form.get('password')
        
        user = User.query.filter((User.username==email_or_username) | (User.email==email_or_username)).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check details.', 'error')

    return render_template('customer-login.html') # Using customer-login generic template

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and user.role == 'admin' and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials', 'error')

    return render_template('admin-login.html')

@app.route('/logout')
def customer_logout():
    logout_user()
    session.clear()  # Clear entire session
    flash('You have been logged out successfully.', 'success')
    response = redirect(url_for('home'))
    # Prevent browser caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/admin-logout')
def admin_logout():
    logout_user()
    session.clear()  # Clear entire session
    flash('You have been logged out.', 'info')
    response = redirect(url_for('admin_login'))
    # Prevent browser caching
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Add after_request to prevent caching of authenticated pages
@app.after_request
def add_header(response):
    if current_user.is_authenticated:
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# ---------------------------- Forgot Password Routes ----------------------------

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate a unique token
            import secrets
            from datetime import timedelta
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)  # Token valid for 1 hour
            
            # Invalidate any existing tokens for this user
            PasswordResetToken.query.filter_by(user_id=user.id, used=False).update({'used': True})
            db.session.commit()
            
            # Create new token
            reset_token = PasswordResetToken(user_id=user.id, token=token, expires_at=expires_at)
            db.session.add(reset_token)
            db.session.commit()
            
            # In production, send this link via email
            reset_link = url_for('reset_password', token=token, _external=True)
            flash(f'Password reset link has been generated. In production, this would be emailed.', 'info')
            # For demo purposes, show the link (remove in production!)
            flash(f'Reset Link: {reset_link}', 'success')
        else:
            # Don't reveal if email exists or not (security)
            flash('If an account with that email exists, a password reset link has been sent.', 'info')
        
        return redirect(url_for('forgot_password'))
    
    return render_template('forgot-password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    # Find the token
    reset_token = PasswordResetToken.query.filter_by(token=token, used=False).first()
    
    if not reset_token:
        flash('Invalid or expired reset link.', 'error')
        return redirect(url_for('forgot_password'))
    
    if reset_token.expires_at < datetime.utcnow():
        flash('This reset link has expired. Please request a new one.', 'error')
        return redirect(url_for('forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return redirect(url_for('reset_password', token=token))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('reset_password', token=token))
        
        # Update password
        user = reset_token.user
        user.password = bcrypt.generate_password_hash(password).decode('utf-8')
        reset_token.used = True
        db.session.commit()
        
        flash('Your password has been reset successfully! You can now login.', 'success')
        return redirect(url_for('customer_login'))
    
    return render_template('reset-password.html', token=token)

# ---------------------------- Registration Routes ----------------------------

@app.route('/register')
def register_main():
    return render_template('registration.html')

@app.route('/register-customer', methods=['GET', 'POST'])
def register_customer():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return redirect(url_for('register_customer'))
            
        if User.query.filter((User.username==username) | (User.email==email)).first():
            flash('Username or Email already exists.', 'error')
            return redirect(url_for('register_customer'))
            
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(username=username, email=email, password=hashed_password, role='customer')
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now login.', 'success')
        return redirect(url_for('customer_login'))
        
    return render_template('register-customer.html')

@app.route('/register-farmer', methods=['GET', 'POST'])
def register_farmer():
    if request.method == 'POST':
        name = request.form.get('name')
        location = request.form.get('location')
        phone = request.form.get('phone')
        crops = request.form.get('crops')
        
        new_farmer = Farmer(name=name, location=location, phone=phone, crops=crops)
        db.session.add(new_farmer)
        db.session.commit()
        
        flash('Registration submitted! We will contact you soon.', 'success')
        return redirect(url_for('register_main'))
        
    return render_template('register-farmer.html')

@app.route('/register-partner', methods=['GET', 'POST'])
def register_partner():
    if request.method == 'POST':
        business_name = request.form.get('business_name')
        contact_person = request.form.get('contact_person')
        email = request.form.get('email')
        phone = request.form.get('phone')
        partner_type = request.form.get('type')
        
        new_partner = Partner(
            business_name=business_name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            type=partner_type
        )
        db.session.add(new_partner)
        db.session.commit()
        
        flash('Registration submitted! We will contact you soon.', 'success')
        return redirect(url_for('register_main'))
        
    return render_template('register-partner.html')

# ---------------------------- Admin Routes ----------------------------
# Main admin_dashboard route is defined earlier in the file with dynamic stats

@app.route('/products/upload', methods=['GET', 'POST'])
@login_required
def products_upload():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        sku = request.form.get('sku')
        name = request.form.get('name')
        description = request.form.get('description')
        price = request.form.get('price')
        category = request.form.get('category')
        stock = request.form.get('stock')
        image_file = request.files.get('image')
        
        if not sku or not name or not price:
            flash('SKU, Name, and Price are required', 'error')
            return redirect(request.url)
            
        image_filename = None
        if image_file and image_file.filename != '':
            if allowed_file(image_file.filename):
                filename = secure_filename(image_file.filename)
                unique_filename = f"{uuid.uuid4().hex}_{filename}"
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                image_file.save(image_path)
                image_filename = unique_filename
            else:
                flash('Invalid file type', 'error')
                return redirect(request.url)
        
        new_product = Product(
            sku=sku,
            name=name,
            description=description,
            price=float(price),
            category=category,
            stock=int(stock) if stock else 0,
            image_filename=image_filename
        )
        try:
            db.session.add(new_product)
            db.session.commit()
            flash('Product uploaded successfully', 'success')
            return redirect(url_for('products_upload'))
        except Exception as e:
            flash(f'Error: {e}', 'error')
    
    products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template('products-upload.html', products=products)

@app.route('/products/delete/<int:product_id>', methods=['POST'])
@login_required
def delete_product(product_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    product = Product.query.get_or_404(product_id)
    # Delete image file
    if product.image_filename:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], product.image_filename))
        except:
            pass
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully', 'success')
    return redirect(url_for('products_upload'))

@app.route('/gallery-manage', methods=['GET', 'POST'])
@login_required
def gallery_manage():
    if current_user.role != 'admin':
        return redirect(url_for('home'))

    if request.method == 'POST':
        image_file = request.files.get('image')
        caption = request.form.get('caption', '')
        category = request.form.get('category', 'Uncategorized')
        
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            image_path = os.path.join(app.config['GALLERY_FOLDER'], unique_filename)
            image_file.save(image_path)
            
            new_item = GalleryItem(filename=unique_filename, caption=caption, category=category)
            db.session.add(new_item)
            db.session.commit()
            flash('Gallery Image Uploaded', 'success')
            return redirect(url_for('gallery_manage'))
        else:
            flash('Invalid image', 'error')
            
    gallery_items = GalleryItem.query.order_by(GalleryItem.created_at.desc()).all()
    return render_template('gallery-manage.html', gallery_items=gallery_items)

@app.route('/gallery-manage/delete/<int:item_id>', methods=['POST'])
@login_required
def delete_gallery_item_route(item_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    
    item = GalleryItem.query.get_or_404(item_id)
    # Optional: Delete file from disk
    try:
        os.remove(os.path.join(app.config['GALLERY_FOLDER'], item.filename))
    except:
        pass
    
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted', 'success')
    return redirect(url_for('gallery_manage'))

@app.route('/farmers-manage')
@login_required
def farmers_manage():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    farmers = Farmer.query.all()
    return render_template('farmers-manage.html', farmers=farmers)

@app.route('/partners-manage')
@login_required
def partners_manage():
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    partners = Partner.query.all()
    return render_template('partners-manage.html', partners=partners)

@app.route('/approve-farmer/<int:farmer_id>')
@login_required
def approve_farmer(farmer_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    farmer = Farmer.query.get_or_404(farmer_id)
    farmer.status = 'approved'
    db.session.commit()
    flash('Farmer approved successfully!', 'success')
    return redirect(url_for('farmers_manage'))

@app.route('/reject-farmer/<int:farmer_id>')
@login_required
def reject_farmer(farmer_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    farmer = Farmer.query.get_or_404(farmer_id)
    farmer.status = 'rejected'
    db.session.commit()
    flash('Farmer rejected.', 'info')
    return redirect(url_for('farmers_manage'))

@app.route('/delete-partner/<int:partner_id>')
@login_required
def delete_partner(partner_id):
    if current_user.role != 'admin':
        return redirect(url_for('home'))
    partner = Partner.query.get_or_404(partner_id)
    db.session.delete(partner)
    db.session.commit()
    flash('Partner deleted.', 'success')
    return redirect(url_for('partners_manage'))

# ---------------------------- Static & Main ----------------------------
@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True, host='0.0.0.0')