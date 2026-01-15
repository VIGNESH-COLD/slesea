# Suvai Organics E-Commerce Platform

A full-stack Flask application for selling organic products, featuring a complete customer shopping experience and a comprehensive admin management dashboard.

## 📋 Prerequisites

- **Python 3.8+**
- **pip** (Python package manager)
- **Virtual Environment** (recommended)

## 🚀 Installation & Setup

1. **Navigate to the project directory:**
   ```powershell
   cd "path/to/suvai-organics"
   ```

2. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\activate
     ```
   - **Type:** You should see `(venv)` at the start of your command line.

4. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

## 🐳 Docker Setup (Recommended)

Run the application in a container without installing Python locally.

1. **Install Docker Desktop**.
2. **Start the application:**
   ```powershell
   docker-compose up --build
   ```
3. **Access the website:** [http://localhost:5000](http://localhost:5000)
4. **Stop the application:** Press `Ctrl+C` or run:
   ```powershell
   docker-compose down
   ```

## ▶️ How to Start the Website (Manual)

1. **Ensure your virtual environment is activated** (`(venv)` is visible).
2. **Run the Flask application:**
   ```powershell
   python app.py
   ```
3. **Open your browser** and visit:
   - [http://localhost:5000](http://localhost:5000)

## 🛑 How to Stop the Website

1. Go to the terminal where the server is running.
2. Press **`Ctrl + C`** to stop the server.
3. To exit the virtual environment, type:
   ```powershell
   deactivate
   ```

## 📖 How to Use

### 👤 Customer Features
- **Browse Products**: Visit the **Products** page to view and search for items.
- **Register/Login**: Create a customer account to save your order history.
- **Shopping Cart**: Add items to your cart. The cart is saved in your session.
- **Checkout**: Place an order (login verified).
- **Profile**: View your past orders and status.

### 🔑 Admin Features
- **Admin Login**: Access the admin panel at `/admin-login`.
  - *Note: Check database or ask administrator for initial credentials.*
- **Dashboard**: View real-time sales stats, recent orders, and inventory counts.
- **Manage Products**: Add, edit, or delete products (`/products/upload`).
- **Manage Orders**: View order details and update status (`Pending` -> `Shipped` -> `Delivered`).
- **Manage Farmers/Partners**: Approve or reject registrations.
- **Gallery**: Upload images to the gallery.

## 📂 Project Structure

- `app.py`: Main application entry point (Routes, Models, Config).
- `templates/`: HTML files for frontend.
  - `layout.html` / `admin-layout.html`: Base templates.
- `static/`: CSS, JavaScript, and Images (`uploads/`, `images/`).
- `instance/`: SQLite database file (`suvai.db`).

## 🛠️ Troubleshooting

- **404 Errors**: Ensure URL is correct.
- **Database Errors**: Delete `instance/suvai.db` and restart `app.py` to re-initialize (Warning: Data loss).
- **Dependency Issues**: Run `pip install -r requirements.txt` again.
