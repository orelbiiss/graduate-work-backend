import os
from pathlib import Path
from fastapi import HTTPException, UploadFile

# Папка для хранения изображений
UPLOAD_DIR = Path("static/img/")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_image(file: UploadFile, filename: str) -> str:
    # Удаляем старый файл, если он существует
    file_location = UPLOAD_DIR / filename
    if file_location.exists():
        os.remove(file_location)

    # Сохраняем новый файл
    try:
        with open(file_location, "wb") as buffer:
            buffer.write(file.file.read())
        return f"static/img/{filename}"  # Возвращаем путь к файлу
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при сохранении файла: {str(e)}")


# Функция для удаления изображения
def delete_image(filename: str):
    try:
        # Формируем путь к файлу
        file_location = UPLOAD_DIR / filename

        # Проверяем, существует ли файл и является ли это файлом
        if file_location.exists() and file_location.is_file():
            # Удаляем файл
            os.remove(file_location)
        else:
            # Если файл не существует, возбуждаем исключение
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        # Если произошла ошибка при удалении, возбуждаем исключение с деталями ошибки
        raise HTTPException(status_code=500, detail="Error deleting file: " + str(e))