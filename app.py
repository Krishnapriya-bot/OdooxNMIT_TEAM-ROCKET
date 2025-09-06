from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import cloudinary
import cloudinary.uploader

from flask import render_template
from flask_login import login_required, current_user



# configure with your Cloudinary account credentials
cloudinary.config( 
  cloud_name = "dqe6pcfu1", 
  api_key = "265411233144585", 
  api_secret = "iskIKE0EV55pzAxPUBxTZIkBqh8" 
)

app = Flask(__name__)
app.config['SECRET_KEY'] = "supersecretkey"
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///ecofinds.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# ---------------- MODELS ---------------- #
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    profile_pic = db.Column(db.String(300), default="https://via.placeholder.com/150")
    dob = db.Column(db.Date, nullable=True)
    address = db.Column(db.String(200), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    pin_code = db.Column(db.String(20), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    country = db.Column(db.String(100), nullable=True)

    products = db.relationship("Product", backref="owner", lazy=True)
    cart_items = db.relationship("Cart", backref="user", lazy=True)
    orders = db.relationship("Order", backref="user", lazy=True)
    
    def is_profile_complete(self):
        return all([
            self.dob,
            self.address,
            self.city,
            self.pin_code,
            self.state,
            self.country
        ])

    # ------------------
    # Calculate age dynamically
    # ------------------
    def age(self):
        if self.dob:
            today = date.today()
            return today.year - self.dob.year - ((today.month, today.day) < (self.dob.month, self.dob.day))
        return None
    
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Float, nullable=False)
    image_url = db.Column(db.String(300), default="https://via.placeholder.com/150")

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    cart_items = db.relationship("Cart", backref="product", lazy=True)
    orders = db.relationship("Order", backref="product", lazy=True)


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, default=1)
    purchased_at = db.Column(db.DateTime, default=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"), nullable=False)


# ---------------- LOGIN MANAGER ---------------- #
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ---------------- ROUTES ---------------- #
@app.route("/")
def home():
    products = Product.query.all()
    return render_template("products2.html", products=products)


@app.route("/ecofinds")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        username = request.form["username"]
        password = request.form["password"]

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please log in instead.", "danger")
            return redirect(url_for("login"))

        hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")
        user = User(email=email, username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid email or password", "danger")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "info")
    return redirect(url_for("home"))

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


@app.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]
        file = request.files.get("profile_pic")

        # update username/email
        current_user.username = username
        current_user.email = email

        # update password only if filled
        if password.strip():
            current_user.password = bcrypt.generate_password_hash(password).decode("utf-8")

        # update profile picture if uploaded
        if file and file.filename != "":
            upload_result = cloudinary.uploader.upload(file)
            current_user.profile_pic = upload_result["secure_url"]

        # update address details
        dob_str = request.form.get("dob")
        if dob_str:
            try:
                current_user.dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
            except ValueError:
                flash("Invalid date format for DOB. Please use YYYY-MM-DD.", "danger")
                return redirect(url_for("edit_profile"))
        else:
            current_user.dob = None
        current_user.address = request.form.get("address")
        current_user.city = request.form.get("city")
        current_user.pin_code = request.form.get("pin_code")
        current_user.state = request.form.get("state")
        current_user.country = request.form.get("country")

        db.session.commit()
        flash("Profile updated successfully!", "success")
        return redirect(url_for("profile"))

    return render_template("edit_profile.html", user=current_user)



@app.route("/product/add", methods=["GET", "POST"])
@login_required
def add_product():
    
    if not current_user.is_profile_complete():
        flash("Please complete your profile before listing a product.", "warning")
        return redirect(url_for("edit_profile"))
    
    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        category = request.form["category"]
        price = float(request.form["price"])

        # handle file upload
        image_url = "https://via.placeholder.com/150"
        if "image" in request.files:
            file = request.files["image"]
            if file.filename != "":
                upload_result = cloudinary.uploader.upload(file)
                image_url = upload_result["secure_url"]

        product = Product(
            title=title,
            description=description,
            category=category,
            price=price,
            image_url=image_url,
            owner=current_user
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully!", "success")
        return redirect(url_for("home"))

    return render_template("add_product.html")



@app.route("/product/<int:product_id>")
def product_details(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_details.html", product=product)


@app.route("/cart")
@login_required
def cart():
    cart_items = Cart.query.filter_by(user_id=current_user.id).all()
    return render_template("cart.html", cart_items=cart_items)


@app.route("/cart/add/<int:product_id>")
@login_required
def add_to_cart(product_id):
    cart_item = Cart(user_id=current_user.id, product_id=product_id, quantity=1)
    db.session.add(cart_item)
    db.session.commit()
    flash("Product added to cart!", "success")
    return redirect(url_for("cart"))


@app.route("/buy/<int:product_id>")
@login_required
def buy_product(product_id):
    if not current_user.is_profile_complete():
        flash("Please complete your profile before making a purchase.", "warning")
        return redirect(url_for("edit_profile"))

    product = Product.query.get_or_404(product_id)
    order = Order(user_id=current_user.id, product_id=product.id, quantity=1)
    db.session.add(order)
    db.session.commit()

    flash("Purchase successful!", "success")
    return redirect(url_for("home"))


@app.route("/search")
def search():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("home"))  # or your main products listing route
    products = Product.query.filter(
        Product.title.ilike(f"%{query}%") |
        Product.description.ilike(f"%{query}%") |
        Product.category.ilike(f"%{query}%")
    ).all()
    return render_template("products2.html", products=products, search_query=query)

# ---------------- MAIN ---------------- #
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
