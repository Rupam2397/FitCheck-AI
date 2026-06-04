from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import joblib

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)

app.config['SECRET_KEY'] = 'fitcheck_ai_2025_secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fitness.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# =========================
# LOGIN MANAGER
# =========================
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.session_protection = "strong"

# =========================
# LOAD ML MODEL
# =========================
model = joblib.load("model/fitness_model.pkl")

# =========================
# USER MODEL
# =========================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# =========================
# FITNESS MODEL
# =========================
class FitnessRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    height = db.Column(db.Float)
    weight = db.Column(db.Float)
    age = db.Column(db.Integer)
    bmi = db.Column(db.Float)
    category = db.Column(db.String(50))
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

# =========================
# USER LOADER
# =========================
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# =========================
# HOME
# =========================
@app.route('/')
@login_required
def home():
    return render_template('index.html')

# =========================
# REGISTER
# =========================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        hashed_password = generate_password_hash(request.form['password'])

        new_user = User(
            username=request.form['username'],
            email=request.form['email'],
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')

# =========================
# LOGIN
# =========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect('/')

        return "Invalid credentials"

    return render_template('login.html')

# =========================
# LOGOUT
# =========================
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# =========================
# PREDICT BMI
# =========================
@app.route('/predict', methods=['POST'])
@login_required
def predict():

    height = request.form.get('height')
    weight = request.form.get('weight')
    age = request.form.get('age')

    if not height or not weight or not age:
        return "Invalid input"

    height = float(height)
    weight = float(weight)
    age = int(age)

    if height > 3:
        height = height / 100

    bmi = round(weight / (height ** 2), 2)

    prediction = model.predict([[height, weight, age]])
    category = prediction[0]

    if category == "Underweight":
        diet = "High protein diet"
        exercise = "Strength training"
        calories = "2500+ kcal/day"

    elif category == "Normal":
        diet = "Balanced diet"
        exercise = "Cardio + Strength"
        calories = "2000 kcal/day"

    elif category == "Overweight":
        diet = "Low sugar diet"
        exercise = "Running + cycling"
        calories = "1800 kcal/day"

    else:
        diet = "Low carb diet"
        exercise = "Walking + HIIT"
        calories = "1500 kcal/day"

    record = FitnessRecord(
        height=height,
        weight=weight,
        age=age,
        bmi=bmi,
        category=category,
        user_id=current_user.id
    )

    db.session.add(record)
    db.session.commit()

    return render_template(
        "dashboard.html",
        bmi=bmi,
        category=category,
        diet=diet,
        exercise=exercise,
        calories=calories
    )

# =========================
# HISTORY
# =========================
@app.route('/history')
@login_required
def history():

    records = FitnessRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(FitnessRecord.id.desc()).all()

    return render_template("history.html", records=records)

# =========================
# DELETE
# =========================
@app.route('/delete/<int:id>')
@login_required
def delete(id):

    record = FitnessRecord.query.get_or_404(id)

    if record.user_id != current_user.id:
        return "Unauthorized", 403

    db.session.delete(record)
    db.session.commit()

    return redirect('/history')

# =========================
# ANALYTICS
# =========================
@app.route('/analytics')
@login_required
def analytics():

    records = FitnessRecord.query.filter_by(
        user_id=current_user.id
    ).all()

    bmi_values = [r.bmi for r in records]
    dates = [r.date.strftime("%d-%m") for r in records]

    return render_template(
        "analytics.html",
        bmi_values=bmi_values,
        dates=dates
    )

# =========================
# PROFILE (NEW FEATURE)
# =========================
@app.route('/profile')
@login_required
def profile():

    total = FitnessRecord.query.filter_by(
        user_id=current_user.id
    ).count()

    last_record = FitnessRecord.query.filter_by(
        user_id=current_user.id
    ).order_by(FitnessRecord.id.desc()).first()

    return render_template(
        "profile.html",
        total=total,
        last_record=last_record
    )

# =========================
# RUN APP
# =========================
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("Database Ready!")

    app.run(debug=True)
    