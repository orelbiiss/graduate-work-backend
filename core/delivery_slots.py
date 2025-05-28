from datetime import date, time, timedelta, datetime
from sqlmodel import Session, delete
from models.cart_models import DeliveryTimeSlot, DeliveryTimeSlotStatus


def _generate_time_intervals() -> list[str]:
    """Генерация интервалов с перерывами: 10:00-12:00, 12:30-14:30, ..."""
    intervals = []
    current = datetime.combine(date.today(), time(10, 0))  # Начало в 10:00

    while current.time() <= time(22, 0):  # До 22:00
        end = current + timedelta(hours=2)
        intervals.append(f"{current.time().strftime('%H:%M')}-{end.time().strftime('%H:%M')}")
        current = end + timedelta(minutes=30)  # Перерыв 30 минут

    return intervals


def ensure_slots_for_date(db: Session, for_date: date) -> list[DeliveryTimeSlot]:
    """Гарантирует наличие слотов на указанную дату (если их нет — создаёт)"""
    # Удаляем старые слоты для этой даты (если есть)
    db.exec(delete(DeliveryTimeSlot).where(DeliveryTimeSlot.date == for_date))

    # Создаём новые слоты
    slots = []
    for time_slot in _generate_time_intervals():
        slot = DeliveryTimeSlot(
            date=for_date,
            time_slot=time_slot,
            max_orders=5,
            current_orders=0,
            status=DeliveryTimeSlotStatus.AVAILABLE
        )
        db.add(slot)
        slots.append(slot)

    db.commit()
    return slots