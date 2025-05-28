# models/id_mixin.py
from sqlmodel import Session
from id_generator import create_with_unique_id

class IDMixin:
    @classmethod
    def create(cls, session: Session, **kwargs):
        """Создает объект с автоматически сгенерированным уникальным ID"""
        kwargs.pop('model', None)  # Удаляем лишний параметр, если есть
        return create_with_unique_id(session, cls, **kwargs)
