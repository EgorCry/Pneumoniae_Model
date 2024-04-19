from flask import Flask, request, render_template, jsonify, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from image_processoring import handle_uploaded_file, get_image_info, format_time, get_all_images_info
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
import os


app = Flask(__name__)
app.secret_key = 'Wabalabadubdub'

login_manager = LoginManager()
login_manager.init_app(app)


class User(UserMixin):
    def __init__(self, id, first_name, last_name, age, gender, country, city):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.age = age
        self.gender = gender
        self.country = country
        self.city = city


users = []
users_by_username = {}


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return redirect(url_for('login'))
    return render_template('register.html')


@login_manager.user_loader
def load_user(user_id):
    return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('index'))
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


@app.route('/<nickname>/<image_number>')
@login_required
def show_image_info(nickname, image_number):
    # Здесь будет логика для извлечения данных о файле
    image_info = get_image_info(nickname, image_number)
    return render_template('image_info.html', info=image_info)


@app.route('/user_images/<filename>')
@login_required
def user_images(filename):
    return send_from_directory('user_images', filename)


@app.route('/gallery')
@login_required
def show_gallery():
    username = 'test'
    images_info = get_all_images_info(username)
    return render_template('gallery.html', images=images_info, username=username)


if __name__ == '__main__':
    app.run(debug=True)
