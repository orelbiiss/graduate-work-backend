
import requests
import re
from core.config import settings


def translate_text(text: str, target_lang: str = "en") -> str:
    """Перевод текста через Yandex Translate API"""
    try:
        response = requests.post(
            "https://translate.api.cloud.yandex.net/translate/v2/translate",
            headers={
                "Authorization": f"Api-Key {settings.YC_TRANSLATE_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "folderId": settings.YC_FOLDER_ID,
                "texts": [text],
                "targetLanguageCode": target_lang,
            },
            timeout=5
        )
        response.raise_for_status()
        return response.json()["translations"][0]["text"]
    except Exception as e:
        raise ValueError(f"Translation failed: {str(e)}")


def generate_section_id(title: str) -> str:
    """Генерация ID в формате section-<translated_title>"""
    try:
        # Переводим текст
        translated = translate_text(title)

        # Приводим к нижнему регистру и заменяем пробелы на подчеркивания
        clean_id = (
            translated.lower()
            .replace(" ", "_")  # Заменяем пробелы на _
            .replace("-", "_")  # Заменяем дефисы на _
        )

        # Удаляем все спецсимволы, кроме букв, цифр и _
        clean_id = re.sub(r"[^\w_]", "", clean_id)

        # Формируем окончательный ID
        return f"section-{clean_id}"

    except Exception as e:
        raise ValueError(f"ID generation failed: {str(e)}")