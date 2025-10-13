import secrets
import sys
import os
import uuid

# Додаємо батьківську папку до path щоб імпортувати модулі
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from storage.database import SessionLocal, init_db
from storage.models import ActivationCode


def get_device_id() -> str:
    """Отримує унікальний ID пристрою (MAC address)"""
    try:
        # На Pi можна отримати реальний MAC
        import subprocess

        mac = subprocess.check_output("cat /sys/class/net/eth0/address", shell=True)
        return mac.decode().strip().replace(":", "").upper()
    except Exception:
        # Fallback - генеруємо UUID
        return uuid.uuid4().hex[:12].upper()


def generate_code() -> str:
    """Генерує красивий код типу VBOT-A3K9-L2M7-X8Q4"""
    parts = []
    for _ in range(4):
        part = secrets.token_hex(2).upper()  # 4 символи (hex -> 2 байти)
        parts.append(part)
    return f"VBOT-{'-'.join(parts)}"


def main() -> None:
    """Генерує код активації для нового пристрою"""
    print("\n" + "=" * 50)
    print("🤖 VOICEBOT - Генерація коду активації")
    print("=" * 50 + "\n")

    # Ініціалізуємо БД
    init_db()
    db = SessionLocal()

    # Перевіряємо чи вже є код для цього пристрою
    device_id = get_device_id()
    existing = db.query(ActivationCode).filter(ActivationCode.device_id == device_id).first()

    if existing:
        print("⚠️  Код для цього пристрою вже існує:")
        print(f"   Device ID: {existing.device_id}")
        print(f"   Code: {existing.code}")
        print(f"   Status: {'✅ Activated' if existing.is_activated else '⏳ Not activated'}")

        response = input("\nСтворити новий код? (yes/no): ")
        if response.lower() != "yes":
            print("❌ Скасовано")
            db.close()
            return

        # Видаляємо старий
        db.delete(existing)
        db.commit()

    # Генеруємо новий код
    code = generate_code()

    activation = ActivationCode(code=code, device_id=device_id, is_activated=False)

    db.add(activation)
    db.commit()

    print("\n" + "=" * 50)
    print("✅ НОВИЙ КОД СТВОРЕНО")
    print("=" * 50)
    print(f"Device ID:  {device_id}")
    print(f"Code:       {code}")
    print("=" * 50)
    print("\n📋 Інструкції:")
    print("1. Надрукуй цей код на наклейці")
    print("2. Приклей на коробку пристрою")
    print("3. Користувач введе цей код в Telegram боті\n")

    db.close()


if __name__ == "__main__":
    main()