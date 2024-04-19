from flask import Flask, flash, request, render_template, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from image_processoring import handle_uploaded_file, get_image_info, format_time, get_all_images_info
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Flask
from flask_login import LoginManager
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.secret_key = 'Wabalabadubdub'
db = SQLAlchemy(app)

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
def upload_file():
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
        return render_template('upload.html')


@app.route('/<nickname>/<image_number>')
@login_required
def show_image_info(nickname, image_number):
    nickname = '_'.join(nickname.split())
    image_info = get_image_info(nickname, image_number)
    return render_template('image_info.html', info=image_info)


@app.route('/user_images/<filename>')
@login_required
def user_images(filename):
    return send_from_directory('user_images', filename)


@app.route('/gallery')
@login_required
def show_gallery():
    username = f"{current_user.first_name} {current_user.last_name}"
    images_info = get_all_images_info(current_user.first_name, current_user.last_name)
    return render_template('gallery.html', images=images_info, username=username)


@app.route('/logout', methods=['POST'])
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
