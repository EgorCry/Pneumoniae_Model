from flask import Flask, flash, request, render_template, jsonify, redirect, url_for, send_from_directory, session
from werkzeug.utils import secure_filename
from image_processoring import handle_uploaded_file, get_image_info, format_time, get_all_images_info, is_doctor
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager
from sqlalchemy.exc import IntegrityError
from flask_migrate import Migrate
from functools import wraps


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.secret_key = 'Wabalabadubdub'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    country = db.Column(db.String(50))
    city = db.Column(db.String(50))
    username = db.Column(db.String(50), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='patient')  # 'doctor' для врачей

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


with app.app_context():
    db.create_all()


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        user_exists = User.query.filter_by(username=username).first()

        if user_exists:
            flash('Это имя пользователя уже занято. Пожалуйста, выберите другое.')
            return render_template('register.html')

        user = User(
            first_name=request.form['first_name'],
            last_name=request.form['last_name'],
            age=request.form['age'],
            gender=request.form['gender'],
            country=request.form['country'],
            city=request.form['city'],
            username=username
        )
        user.set_password(request.form['password'])
        db.session.add(user)
        try:
            db.session.commit()
            login_user(user)
            return redirect(url_for('show_gallery'))
        except IntegrityError:
            db.session.rollback()
            flash('Произошла ошибка при регистрации. Пожалуйста, попробуйте снова.')
            return render_template('register.html')

    return render_template('register.html')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('show_gallery'))
        else:
            flash('Неверный логин или пароль')
            return render_template('login.html')
    return render_template('login.html')


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file(patient_id=None):
    if request.method == 'POST':
        if 'image' not in request.files:
            return "Файл не найден", 400

        file = request.files['image']
        if file.filename == '':
            return "Файл не выбран", 400

        if file:
            response = handle_uploaded_file(file)
            return redirect(response)
    else:
        return render_template('upload.html', patient_id=patient_id)


@app.route('/user/<int:user_id>/image/<int:image_number>')
@login_required
def show_image_info(user_id, image_number):
    if current_user.role != 'doctor' and current_user.id != user_id:
        flash('У вас нет доступа к этой галерее.')
        return redirect(url_for('show_gallery'))
    user = User.query.get(user_id)
    image_info = get_image_info(user_id, image_number, user)
    return render_template('image_info.html', info=image_info)


@app.route('/user_images/<filename>')
@login_required
def user_images(filename):
    return send_from_directory('user_images', filename)


@app.route('/gallery')
@login_required
def show_gallery():
    if current_user.role == 'doctor':
        return redirect(url_for('doctor_dashboard'))
    images_info, username = get_all_images_info(current_user)
    username = f"{current_user.first_name} {current_user.last_name}"
    return render_template('gallery.html', images=images_info, patient_name=username)


def doctor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_doctor(current_user):
            flash('У Вас нет доступа к этому разделу. Возвращаем Вас в раздел галереи.')
            return redirect(url_for('show_gallery'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/doctor')
@login_required
@doctor_required
def doctor_dashboard():
    patients = User.query.filter_by(role='patient').all()
    return render_template('doctor_dashboard.html', patients=patients)


# Функция для добавления пользователя-врача в базу данных при запуске
def add_doctor_to_db():
    # Проверка, существует ли уже пользователь с данным username
    doctor_exists = User.query.filter_by(username='drhouse').first()

    # Если пользователя нет, создаем нового
    if not doctor_exists:
        doctor = User(
            first_name='Gregory',
            last_name='House',
            age=56,
            gender='Мужчина',
            country='Russia',
            city='Moscow',
            username='drhouse',
            role='doctor'
        )
        doctor.set_password('password')

        db.session.add(doctor)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()


@app.route('/patient_gallery/<int:patient_id>')
@login_required
@doctor_required
def patient_gallery(patient_id):
    patient = User.query.get_or_404(patient_id)
    if patient.role != 'patient':
        flash('Выбранный пользователь не является пациентом.')
        return redirect(url_for('doctor_dashboard'))
    images_info, patient_name = get_all_images_info(patient)
    username = f"{patient.first_name} {patient.last_name}"
    return render_template('gallery.html', images=images_info, patient_name=patient_name, user_id=patient_id)


@app.route('/doctor/patient/<int:user_id>/image/<int:image_number>')
@login_required
@doctor_required
def doctor_patient_image(user_id, image_number):
    patient = User.query.get_or_404(user_id)
    image_info = get_image_info(user_id, image_number, patient)
    return render_template('image_info.html', info=image_info, is_doctor=True, patient=patient)


@app.route('/doctor/patient_gallery/<int:patient_id>')
@login_required
@doctor_required
def doctor_patient_gallery(patient_id):
    patient = User.query.get_or_404(patient_id)
    images_info, patient_name = get_all_images_info(patient)
    return render_template('gallery.html', images=images_info,
                           patient_name=patient_name, patient_id=patient_id, is_doctor=True)


@app.route('/upload_for_patient/<int:patient_id>', methods=['GET', 'POST'])
@login_required
@doctor_required
def upload_for_patient(patient_id):
    patient = User.query.get_or_404(patient_id)
    if request.method == 'POST':
        if 'image' not in request.files:
            flash("Файл не найден")
            return redirect(request.url)

        file = request.files['image']
        if file.filename == '':
            flash("Файл не выбран")
            return redirect(request.url)

        if file:
            response = handle_uploaded_file(file, patient)
            return redirect(response)
    else:
        return render_template('upload_for_patient.html', patient_id=patient_id)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        add_doctor_to_db()
    app.run(debug=True)
