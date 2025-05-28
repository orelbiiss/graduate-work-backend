import boto3
from botocore.exceptions import ClientError, NoCredentialsError
from fastapi import HTTPException, UploadFile
from pathlib import Path
from typing import Optional
import uuid
from core.config import settings


class S3Service:
    def __init__(self):
        self.s3 = boto3.client(
            's3',
            endpoint_url=settings.YC_ENDPOINT_URL,
            aws_access_key_id=settings.YC_ACCESS_KEY_ID,
            aws_secret_access_key=settings.YC_SECRET_ACCESS_KEY
        )
        self.bucket = settings.YC_BUCKET_NAME

    def upload_file(self, file: UploadFile, folder: str,
                    filename: Optional[str] = None) -> str:
        """
        Загружает файл в Yandex Object Storage

        :param file: FastAPI UploadFile объект
        :param folder: Папка в бакете (sections/products)
        :param filename: Имя файла (если None - генерируется автоматически)
        :return: Публичный URL файла
        """
        try:
            # Генерация имени файла если не указано
            if not filename:
                ext = Path(file.filename).suffix.lower()
                filename = f"{uuid.uuid4()}{ext}"

            key = f"{folder}/{filename}"

            # Загрузка файла
            self.s3.upload_fileobj(
                file.file,
                self.bucket,
                key,
                ExtraArgs={'ContentType': file.content_type}
            )

            return f"https://{self.bucket}.storage.yandexcloud.net/{key}"

        except NoCredentialsError:
            raise HTTPException(
                status_code=500,
                detail="S3 credentials not configured"
            )
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"S3 upload error: {str(e)}"
            )

    def delete_file(self, folder: str, filename: str) -> bool:
        """
        Удаляет файл из хранилища

        :param folder: Папка в бакете
        :param filename: Имя файла
        :return: True если удаление успешно
        """
        try:
            self.s3.delete_object(
                Bucket=self.bucket,
                Key=f"{folder}/{filename}"
            )
            return True
        except ClientError as e:
            raise HTTPException(
                status_code=500,
                detail=f"S3 delete error: {str(e)}"
            )


# Создаем экземпляр сервиса для импорта в другие модули
s3_service = S3Service()