import os
from datetime import datetime
from PIL import Image
import pydicom
import hashlib
import numpy as np
from keras.models import load_model
import joblib
from io import BytesIO
import tensorflow as tf

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # 0 = all messages are logged (default behavior)
                                          # 1 = INFO messages are not printed
                                          # 2 = INFO and WARNING messages are not printed
                                          # 3 = INFO, WARNING, and ERROR messages are not printed


USER_IMAGES_DIR = 'user_images'
keras_model = load_model('models/big_dataset_model.keras')
logistic_model = joblib.load('models/logistic_regression.pkl')


def handle_uploaded_file(file):
    extension = file.filename.rsplit('.', 1)[1].lower()
    if extension in ['jpeg', 'jpg', 'png']:
        image = Image.open(BytesIO(file.read()))
        return save_image(image, extension)
    elif extension == 'dcm':
        file = convert_dicom_to_jpeg(file)
        return save_image(file, extension)
    else:
        return "Unsupported file format", 400


def convert_dicom_to_jpeg(file_stream):
    dicom_data = pydicom.dcmread(file_stream)
    image_array = dicom_data.pixel_array
    image = Image.fromarray(image_array)
    return image


def save_image(image, format):
    nickname = 'test'
    image_number = count_user_images(nickname) + 1
    current_time = datetime.now().strftime("%Y-%m-%d-%H-%M")

    prepared_image = prepare_image(image)
    predictions = keras_model.predict(prepared_image)
    calibrated_prediction = logistic_model.predict_proba(predictions)[:, 1]
    probability = round(calibrated_prediction[0], 2)

    filename = f"{nickname}_{image_number}_{current_time}_{probability}.jpeg"
    path = os.path.join(USER_IMAGES_DIR, filename)

    if format == 'jpeg':
        image.save(path, 'JPEG')
    else:
        image.save(path, 'JPEG')

    redirect_url = f"/{nickname}/{image_number}"
    return redirect_url


def count_user_images(nickname):
    os.makedirs(USER_IMAGES_DIR, exist_ok=True)
    max_number = 0
    for filename in os.listdir(USER_IMAGES_DIR):
        if filename.startswith(nickname):
            number = int(filename.split('_')[1])
            max_number = max(max_number, number)
    return max_number


def prepare_image(image):
    image = image.resize((512, 512))
    image_array = np.array(image)
    if len(image_array.shape) == 2:  # Проверка, одноканальное ли это изображение
        image_array = np.stack((image_array,)*3, axis=-1)  # Преобразование в трехканальное изображение
    image_array = np.expand_dims(image_array, axis=0)  # Добавление размерности batch
    return image_array


def get_image_info(nickname, image_number):
    for filename in os.listdir(USER_IMAGES_DIR):
        if filename.startswith(f"{nickname}_{image_number}"):
            parts = filename.rsplit('_', 3)
            probability = parts[-1].rsplit('.', 1)[0]
            time = parts[-2]
            formatted_date_time = format_time(time)
            result = 'Низкая вероятность пневмонии' if (float(probability) <= 0.12) \
                else 'Высокая вероятность пневмонии'
            return {
                'username': nickname,
                'date': formatted_date_time.get('date'),
                'time': formatted_date_time.get('time'),
                'probability': probability,
                'image_path': filename,
                'result': result
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


def get_all_images_info(nickname):
    images_info = []
    files = os.listdir(USER_IMAGES_DIR)
    sorted_files = sorted(files, key=extract_image_number)
    for filename in sorted_files:
        if filename.startswith(nickname):
            parts = filename.split('_')
            image_number = parts[1]
            date_time_str = parts[2]
            probability = parts[3].rsplit('.', 1)[0]
            result = 'Низкая вероятность пневмонии' if (float(probability) <= 0.12) \
                else 'Высокая вероятность пневмонии'
            formatted_date_time = format_time(date_time_str)
            images_info.append({
                'number': image_number,
                'date': formatted_date_time.get('date'),
                'time': formatted_date_time.get('time'),
                'probability': probability,
                'file_name': filename,
                'result': result
            })
    return images_info
