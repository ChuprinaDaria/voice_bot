import os
import argparse
import qrcode
from qrcode.constants import ERROR_CORRECT_L


def generate_bot_qr(bot_username):
    """Генерує QR код для швидкого відкриття бота"""

    # Deep link на бота
    bot_link = f"https://t.me/{bot_username}?start=welcome"

    # Створюємо QR
    qr = qrcode.QRCode(
        version=1,
        error_correction=ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(bot_link)
    qr.make(fit=True)

    # Зберігаємо картинку
    img = qr.make_image(fill_color="black", back_color="white")
    # Зберігаємо через qrcode image API у двійковий потік
    with open("bot_qr_code.png", "wb") as f:
        img.save(f, kind="PNG")

    print("✅ QR код збережений: bot_qr_code.png")
    print(f"📱 Лінк: {bot_link}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Генерація QR-коду для Telegram бота")
    parser.add_argument("--username", dest="username", help="username бота без @")
    args = parser.parse_args()

    username = args.username or os.getenv("BOT_USERNAME")
    if not username:
        try:
            username = input("Введи username твого бота (без @): ")
        except EOFError:
            raise SystemExit(
                "Не вдалось прочитати username. Передай --username або змінну оточення BOT_USERNAME."
            )

    if not username:
        raise SystemExit("Username бота порожній. Передай коректне значення.")

    generate_bot_qr(username)


