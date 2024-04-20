import os
from datetime import datetime
from PIL import Image
import pydicom
import numpy as np
from keras.models import load_model
import joblib
from io import BytesIO
from flask import url_for


os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0 = all messages are logged (default behavior)
                                          # 1 = INFO messages are not printed
                                          # 2 = INFO and WARNING messages are not printed
                                          # 3 = INFO, WARNING, and ERROR messages are not printed


USER_IMAGES_DIR = 'user_images'
keras_model = load_model('models/big_dataset_model.keras')
logistic_model = joblib.load('models/logistic_regression.pkl')


def handle_uploaded_file(file, patient=None):
    extension = file.filename.rsplit('.', 1)[1].lower()
    if extension in ['jpeg', 'jpg', 'png']:
        image = Image.open(BytesIO(file.read()))
        return save_image(image, patient)
    elif extension == 'dcm':
        image = convert_dicom_to_jpeg(file)
        return save_image(image, patient)
    else:
        return "Unsupported file format", 400


def convert_dicom_to_jpeg(file_stream):
    dicom_data = pydicom.dcmread(file_stream)
    image_array = dicom_data.pixel_array
    image = Image.fromarray(image_array)
    return image


def save_image(image, patient):
    patient_id = patient.id
    image_number = str(count_user_images(str(patient_id)) + 1)
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M")

    prepared_image = prepare_image(image)
    predictions = keras_model.predict(prepared_image)
    calibrated_prediction = logistic_model.predict_proba(predictions)[:, 1]
    probability = round(calibrated_prediction[0], 2)

    filename = f"{patient_id}_{image_number}_{current_time}_{probability}.jpeg"
    path = os.path.join(USER_IMAGES_DIR, filename)

    image.save(path, 'JPEG')

    redirect_url = url_for('doctor_patient_image', user_id=patient_id, image_number=image_number)
    return redirect_url


def count_user_images(user_id_str):
    os.makedirs(USER_IMAGES_DIR, exist_ok=True)
    max_number = 0
    for filename in os.listdir(USER_IMAGES_DIR):
        if filename.startswith(user_id_str):
            try:
                number = int(filename.split('_')[1])
                max_number = max(max_number, number)
            except ValueError:
                continue
    return max_number


def prepare_image(image):
    image = image.resize((512, 512))
    image_array = np.array(image)
    if len(image_array.shape) == 2:  # Проверка, одноканальное ли это изображение
        image_array = np.stack((image_array,)*3, axis=-1)  # Преобразование в трехканальное изображение
    image_array = np.expand_dims(image_array, axis=0)  # Добавление размерности batch
    return image_array


def get_image_info(user_id, image_number, user):
    nickname = f"{user.first_name}_{user.last_name}"
    for filename in os.listdir(USER_IMAGES_DIR):
        if filename.startswith(f"{user_id}_{image_number}"):
            parts = filename.rsplit('_', 3)
            probability = parts[-1].rsplit('.', 1)[0]
            time = parts[-2]
            formatted_date_time = format_time(time)
            result = 'Низкая вероятность пневмонии' if float(probability) <= 0.12 else 'Высокая вероятность пневмонии'
            return {
                'date': formatted_date_time.get('date'),
                'time': formatted_date_time.get('time'),
                'probability': probability,
                'image_path': filename,
                'result': result,
                'user_id': user_id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'age': user.age,
                'gender': 'Мужчина' if user.gender == 'male' else 'Женщина',
                'country': user.country,
                'city': user.city
            }
    return None


def format_time(time_str):
    # Преобразование строки времени в читаемый формат
    dt = datetime.strptime(time_str, "%Y-%m-%d-%H-%M")
    return {
        'date': dt.strftime("Дата: %d %B %Y года"),
        'time': dt.strftime("Время: %H часов %M минут")
    }


def extract_image_number(filename):
    return int(filename.split('_')[1])


def get_all_images_info(patient):
    user_id_str = str(patient.id)
    patient_name = patient.first_name + ' ' + patient.last_name
    images_info = []
    files = os.listdir(USER_IMAGES_DIR)
    sorted_files = sorted(
        (f for f in files if f.startswith(f"{user_id_str}_")),
        key=lambda x: int(x.split('_')[1])
    )
    for filename in sorted_files:
        parts = filename.split('_')
        image_number = parts[1]
        timestamp = parts[2]
        probability_str = '.'.join([parts[3].split('.')[0], parts[3].split('.')[1]])
        probability = float(probability_str)
        formatted_date_time = format_time(timestamp)
        result = 'Низкая вероятность пневмонии' if probability <= 0.12 else 'Высокая вероятность пневмонии'
        images_info.append({
            'user_id': user_id_str,
            'number': image_number,
            'date': formatted_date_time['date'],
            'time': formatted_date_time['time'],
            'probability': f"{probability:.2f}",
            'file_name': filename,
            'result': result
        })
    return images_info, patient_name


def is_doctor(user):
    return user.role == 'doctor'
