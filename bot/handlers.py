from __future__ import annotations

from datetime import datetime
import re

from telegram import Update
from telegram.ext import ContextTypes

from storage.database import SessionLocal
from storage.models import ActivationCode, User, Conversation
from .keyboards import main_menu_keyboard, setup_menu_keyboard, api_keys_keyboard, language_keyboard, voice_control_keyboard, music_control_keyboard
from core.state_manager import voice_daemon_manager
from core.api_manager import api_manager
from integrations.mopidy import mopidy_manager
from integrations.google_calendar import google_calendar_manager
import random


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Початок роботи з ботом"""
    tg_user = update.effective_user
    message = update.message

    if tg_user is None or message is None:
        return

    # Якщо користувач вже активований — показуємо меню налаштувань одразу
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == tg_user.id).first()
    finally:
        db.close()

    if user:
        await message.reply_text(
            "⚙️ Меню налаштувань:" if user.language == "uk" else "⚙️ Settings menu:",
            reply_markup=setup_menu_keyboard(user.language),
        )
        return

    # Якщо користувач ще не налаштований — спочатку обираємо мову
    await message.reply_text(
        "Please choose your language:", reply_markup=language_keyboard()
    )
    user_data = getattr(context, "user_data", None)
    if isinstance(user_data, dict):
        user_data["awaiting_language_choice"] = True


async def activate_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Активація за кодом"""
    tg_user = update.effective_user
    message = update.message

    if tg_user is None or message is None:
        return

    user_id = tg_user.id
    raw_text = message.text or ""
    match = re.search(r"VBOT-[A-F0-9\-]{4,}", raw_text, flags=re.IGNORECASE)
    if not match:
        await message.reply_text("❌ Невірний код активації")
        return
    code = match.group(0).upper()

    db = SessionLocal()

    try:
        activation = db.query(ActivationCode).filter(ActivationCode.code == code).first()

        if not activation:
            await message.reply_text("❌ Невірний код активації")
            return

        if activation.is_activated:
            await message.reply_text("❌ Цей код вже використовується")
            return

        activation.is_activated = True
        activation.telegram_user_id = user_id
        activation.activated_at = datetime.utcnow()

        # Якщо мову було вибрано до активації — використовуємо її
        selected_lang = "uk"
        user_data = getattr(context, "user_data", None)
        if isinstance(user_data, dict) and user_data.get("selected_lang") in {"uk", "en"}:
            selected_lang = user_data["selected_lang"]

        user = User(
            telegram_user_id=user_id,
            device_id=activation.device_id,
            language=selected_lang,
        )

        db.add(user)
        db.commit()

        await message.reply_text(
            "🎉 Активація успішна!\n\n"
            "Тепер налаштуй свій VoiceBot:",
            reply_markup=setup_menu_keyboard(user.language),
        )
    finally:
        db.close()


async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка кнопок меню"""
    tg_user = update.effective_user
    message = update.message

    if tg_user is None or message is None:
        return

    text = message.text
    user_id = tg_user.id
    db = SessionLocal()

    user = db.query(User).filter(User.telegram_user_id == user_id).first()

    # Спочатку — зміна мови (дозволено навіть до активації)
    if text in ["Українська (uk)", "English (en)", "Deutsch (de)"]:
        if "Українська" in text:
            new_lang = "uk"
        elif "Deutsch" in text:
            new_lang = "de"
        else:
            new_lang = "en"
        if user:
            user.language = new_lang
            db.commit()
            if new_lang == "uk":
                confirm_text = "✅ Мову змінено"
            elif new_lang == "de":
                confirm_text = "✅ Sprache aktualisiert"
            else:
                confirm_text = "✅ Language updated"
            await message.reply_text(confirm_text, reply_markup=setup_menu_keyboard(new_lang))
        else:
            user_data = getattr(context, "user_data", None)
            if isinstance(user_data, dict):
                user_data["selected_lang"] = new_lang
            if new_lang == "uk":
                greet = "👋 Привіт! Я VoiceBot.\n\nВведи код активації з коробки (формат: VBOT-XXXX-XXXX-XXXX)"
            elif new_lang == "de":
                greet = "👋 Hallo! Ich bin VoiceBot.\n\nBitte gib deinen Aktivierungscode ein (Format: VBOT-XXXX-XXXX-XXXX)"
            else:
                greet = "👋 Hi! I'm VoiceBot.\n\nPlease enter your activation code (format: VBOT-XXXX-XXXX-XXXX)"
            await message.reply_text(greet)
        db.close()
        return



    # Відкрити меню налаштувань
    if text in ["⚙️ Налаштування", "⚙️ Settings", "⚙️ Einstellungen"]:
        await message.reply_text(
            "⚙️ Меню налаштувань:" if (user and user.language == "uk") else "⚙️ Settings menu:",
            reply_markup=setup_menu_keyboard(user.language if user else "uk"),
        )
        db.close()
        return

    # Якщо користувач ще не активований — підказка активуватися
    if not user:
        await message.reply_text(
            "❌ Спочатку активуй пристрій.\n"
            "Введи код активації з коробки."
        )
        db.close()
        return

    # Швидкі команди особистості доступні завжди
    if text and text.lower() in ['переглянути', 'view']:
        current = user.personality_prompt or "Не встановлено"
        await message.reply_text(
            f"🗣️ Поточний промпт:\n\n`{current}`",
            parse_mode='Markdown'
        )
        db.close()
        return

    if text and text.lower() in ['скинути', 'reset']:
        user.personality_prompt = None
        db.commit()
        await message.reply_text(
            "✅ Промпт видалено. Бот використовуватиме стандартну поведінку.",
            reply_markup=setup_menu_keyboard(user.language)
        )
        db.close()
        return

    # API Keys - НОВА КНОПКА
    if text in ["🔑 API Ключі", "🔑 API Keys", "🔑 API-Schlüsselverwaltung"]:
        # Перевіряємо чи є користувацький ключ
        current_key = api_manager.get_openai_key(user_id)

        if current_key:
            # Показуємо тільки перші/останні символи
            masked = f"{current_key[:8]}...{current_key[-4:]}"
            status = f"✅ Встановлено: {masked}"
        else:
            status = "⚠️ Використовується системний ключ"

        if user.language == "uk":
            text_msg = (
                "🔑 Керування API ключами\n\n" f"OpenAI: {status}\n\n" "Оберіть дію:"
            )
        else:
            text_msg = (
                "🔑 API Keys Management\n\n" f"OpenAI: {status}\n\n" "Choose action:"
            )

        await message.reply_text(text_msg, reply_markup=api_keys_keyboard(user.language))

    # Вибір мови (кнопка з меню налаштувань)
    elif text in ["🌐 Вибрати мову", "🌐 Choose Language", "🌐 Sprache wählen"]:
        await message.reply_text(
            "Оберіть мову / Choose language:", reply_markup=language_keyboard()
        )

    # OpenAI/Groq API Key
    elif text in ["🔑 OpenAI API Key"]:
        if user.language == "uk":
            text_msg = (
                "🔑 API Ключ (OpenAI або Groq)\n\n"
                "Надішли свій ключ API:\n\n"
                "🔵 **OpenAI** (повільніше):\n"
                "`sk-proj-xxxxxxxxxxxxx`\n"
                "Реєстрація: https://platform.openai.com\n\n"
                "⚡ **Groq** (5x швидше, рекомендую!):\n"
                "`gsk_xxxxxxxxxxxxx`\n"
                "Реєстрація: https://console.groq.com/keys\n\n"
                "⚠️ Ключ зберігається зашифрованим"
            )
        else:
            text_msg = (
                "🔑 API Key (OpenAI or Groq)\n\n"
                "Send your API key:\n\n"
                "🔵 **OpenAI** (slower):\n"
                "`sk-proj-xxxxxxxxxxxxx`\n"
                "Sign up: https://platform.openai.com\n\n"
                "⚡ **Groq** (5x faster, recommended!):\n"
                "`gsk_xxxxxxxxxxxxx`\n"
                "Sign up: https://console.groq.com/keys\n\n"
                "⚠️ Key is stored encrypted"
            )

        await message.reply_text(text_msg, parse_mode="Markdown")
        user_data = getattr(context, "user_data", None)
        if isinstance(user_data, dict):
            user_data["awaiting_openai_key"] = True

    # Керування голосом (меню)
    elif text in ["🎤 Голосовий режим", "🎤 Voice Control", "🎤 Sprachsteuerung"]:
        await message.reply_text(
            ("Керування голосом" if user.language == "uk" else "Voice control"),
            reply_markup=voice_control_keyboard(user.language)
        )

    # Підключення WiFi (старт)
    elif text in ["📶 Підключити WiFi", "📶 Connect WiFi"]:
        prompt = (
            "Введи дані WiFi у форматі: назва мережі;пароль" if user.language == "uk" else "Send WiFi as: network name;password"
        )
        await message.reply_text(prompt)
        user_data = getattr(context, "user_data", None)
        if isinstance(user_data, dict):
            user_data["awaiting_wifi_creds"] = True

    # Обробка введення WiFi облікових даних
    elif getattr(context, "user_data", {}).get("awaiting_wifi_creds") and text and ";" in text:
        try:
            ssid, password = [part.strip() for part in text.split(";", 1)]
        except Exception:
            ssid, password = "", ""

        if not ssid or not password:
            await message.reply_text(
                "❌ Невірний формат. Приклад: my_wifi;my_password" if user.language == "uk" else "❌ Invalid format. Example: my_wifi;my_password"
            )
        else:
            from hardware.wifi_manager import wifi_manager
            await message.reply_text("🔄 Підключаю..." if user.language == "uk" else "🔄 Connecting...")
            ok, info = wifi_manager.connect_to_wifi(ssid, password)
            if ok:
                await message.reply_text(
                    "✅ Підключено до WiFi" if user.language == "uk" else "✅ Connected to WiFi"
                )
            else:
                await message.reply_text(
                    info if user.language == "uk" else (info.replace("Підключено", "Connected") if info else "❌ Failed to connect")
                )

        ud = getattr(context, "user_data", None)
        if isinstance(ud, dict):
            ud["awaiting_wifi_creds"] = False

    # Spotify
    elif text in ["🎵 Spotify", "🎵 Музика", "🎵 Music"]:
        # Перевіряємо чи запущений Mopidy
        if mopidy_manager.is_running():
            if user.language == "uk":
                await message.reply_text(
                    "✅ Музичний сервер працює!\n\n"
                    "🎵 Доступні команди голосом:\n"
                    "• 'Грай Imagine Dragons'\n"
                    "• 'Включи музику'\n"
                    "• 'Пауза'\n"
                    "• 'Наступна пісня'\n\n"
                    "📖 Mopidy шукає музику на:\n"
                    "✅ Spotify\n"
                    "✅ YouTube Music\n"
                    "✅ Локальні файли\n\n"
                    "⚙️ Налаштування: /etc/mopidy/mopidy.conf",
                    parse_mode='Markdown'
                )
            else:
                await message.reply_text(
                    "✅ Music server is running!\n\n"
                    "🎵 Available voice commands:\n"
                    "• 'Play Imagine Dragons'\n"
                    "• 'Play music'\n"
                    "• 'Pause'\n"
                    "• 'Next song'\n\n"
                    "📖 Mopidy searches music on:\n"
                    "✅ Spotify\n"
                    "✅ YouTube Music\n"
                    "✅ Local files\n\n"
                    "⚙️ Settings: /etc/mopidy/mopidy.conf",
                    parse_mode='Markdown'
                )
        else:
            if user.language == "uk":
                await message.reply_text(
                    "❌ Музичний сервер не запущений\n\n"
                    "📖 Для запуску:\n"
                    "```bash\n"
                    "sudo systemctl start mopidy\n"
                    "```\n\n"
                    "📚 Інструкція з налаштування: MOPIDY_SETUP.md",
                    parse_mode='Markdown'
                )
            else:
                await message.reply_text(
                    "❌ Music server not running\n\n"
                    "📖 To start:\n"
                    "```bash\n"
                    "sudo systemctl start mopidy\n"
                    "```\n\n"
                    "📚 Setup guide: MOPIDY_SETUP.md",
                    parse_mode='Markdown'
                )

    # Google Calendar
    elif text in ["📅 Календар", "📅 Підключити Google Calendar", "📅 Connect Google Calendar"]:
        if google_calendar_manager.is_connected(user_id):
            if user.language == "uk":
                await message.reply_text(
                    "✅ Google Calendar вже підключено!\n\n"
                    "Щоб створити подію, надішли:\n"
                    "`Подія: Назва | YYYY-MM-DD HH:MM`\n\n"
                    "Приклад:\n"
                    "`Подія: Зустріч | 2025-10-15 14:30`",
                    parse_mode='Markdown'
                )
            else:
                await message.reply_text(
                    "✅ Google Calendar already connected!\n\n"
                    "To create event, send:\n"
                    "`Event: Name | YYYY-MM-DD HH:MM`\n\n"
                    "Example:\n"
                    "`Event: Meeting | 2025-10-15 14:30`",
                    parse_mode='Markdown'
                )
        else:
            if user.language == "uk":
                text_msg = (
                    "📅 Підключення Google Calendar (спрощений спосіб)\n\n"
                    "📖 Інструкція:\n"
                    "1. Іди на https://developers.google.com/oauthplayground\n"
                    "2. У лівій панелі натисни '+ Add scopes'\n"
                    "3. Знайди 'Calendar API v3' → обери `.../auth/calendar.readonly`\n"
                    "4. Натисни 'Authorize APIs' (синя кнопка)\n"
                    "5. Дозволь доступ до календаря\n"
                    "6. Натисни 'Exchange authorization code for tokens'\n"
                    "7. Скопіюй **Access token** (не refresh!)\n"
                    "8. Надішли токен сюди\n\n"
                    "⚠️ Токен дійсний ~1 годину\n\n"
                    "💡 Альтернатива: скажи голосом 'Які події сьогодні?'"
                )
            else:
                text_msg = (
                    "📅 Connect Google Calendar (simplified)\n\n"
                    "📖 Instructions:\n"
                    "1. Go to https://developers.google.com/oauthplayground\n"
                    "2. In left panel, click '+ Add scopes'\n"
                    "3. Find 'Calendar API v3' → select `.../auth/calendar.readonly`\n"
                    "4. Click 'Authorize APIs' (blue button)\n"
                    "5. Allow calendar access\n"
                    "6. Click 'Exchange authorization code for tokens'\n"
                    "7. Copy **Access token** (not refresh!)\n"
                    "8. Send token here\n\n"
                    "⚠️ Token valid ~1 hour\n\n"
                    "💡 Alternative: say 'What events today?' by voice"
                )

            await message.reply_text(
                text_msg,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            user_data = getattr(context, "user_data", None)
            if isinstance(user_data, dict):
                user_data['awaiting_google_code'] = True

    # Особистість — тепер статична (динамічне редагування вимкнено)
    elif text in ["🗣️ Особистість", "🗣️ Налаштувати особистість", "🗣️ Setup Personality"]:
        static_prompt = (
            "Тебе звати Орест (Orest). Ти чоловік, веселий, саркастичний  "
            "і безжально критикуєш усе зайве. Ти дуже любиш Україну і час від часу без причини "
            "наспівуєш «Батько наш Бандера, Україна мати». Говори коротко, дотепно, з легкою "
            "іронією, у стилі жартів Леся Подерв’янського (без нецензурщини). Якщо запит "
            "нечіткий — саркастично попроси перефразувати."
        )
        if user.language == "uk":
            await message.reply_text(
                f"🗣️ Особистість бота (статично):\n`{static_prompt}`",
                parse_mode='Markdown'
            )
        else:
            await message.reply_text(
                f"🗣️ Bot Personality (static):\n`{static_prompt}`",
                parse_mode='Markdown'
            )
    
    # Швидке збереження промпту вимкнене — відповідь-сповіщення
    elif isinstance(text, str) and (text.lower().startswith("промпт:") or text.lower().startswith("prompt:")):
        note = (
            "ℹ️ Зміна особистості вимкнена. Використовується статичний промпт."
            if user.language == "uk" else
            "ℹ️ Personality editing is disabled. A static prompt is used."
        )
        await message.reply_text(note)
        db.close()
        return

    # Назад до налаштувань
    elif text in ["🔙 Назад до налаштувань", "🔙 Back to Settings", "🔙 Zurück zu Einstellungen"]:
        await message.reply_text(
            "⚙️ Меню налаштувань:" if user.language == "uk" else "⚙️ Settings menu:",
            reply_markup=setup_menu_keyboard(user.language),
        )

    # Завершити налаштування → головне меню
    elif text in ["✅ Завершити налаштування", "✅ Finish Setup", "✅ Einrichtung abschließen"]:
        await message.reply_text(
            ("Головне меню" if user.language == "uk" else "Main menu"),
            reply_markup=main_menu_keyboard(user.language),
        )
    
    # Керування музикою
    elif text in ["🎵 Керування музикою", "🎵 Musiksteuerung", "🎵 Music Control",
                  "⏸️ Пауза", "⏸️ Pause", "▶️ Продовжити", "▶️ Fortsetzen", "▶️ Resume",
                  "⏭️ Наступна", "⏭️ Nächste", "⏭️ Next", "⏮️ Попередня", "⏮️ Vorherige", "⏮️ Previous",
                  "⏹️ Зупинити музику", "⏹️ Musik stoppen", "⏹️ Stop Music"]:
        db.close()
        await music_control_handler(update, context)
        return
        
    # Таймери
    elif text in ["⏰ Таймер", "⏰ Timer"] or getattr(context, "user_data", {}).get('awaiting_timer'):
        db.close()
        await timer_handler(update, context)
        return
    
    # Історія
    elif text in ["📜 Історія", "📜 Verlauf", "📜 History"]:
        db.close()
        await history_handler(update, context)
        return
    
    # Розваги (жарти/факти)
    elif text in ["🎲 Розважити мене", "🎲 Unterhaltung", "🎲 Entertain me"]:
        db.close()
        await fun_handler(update, context)
        return
    
    # Голосове керування
    elif text in ["🎤 Увімкнути голос", "🎤 Enable Voice", "🎤 Stimme aktivieren",
                  "🔇 Заглушити мікрофон", "🔇 Mute Microphone", "🔇 Mikrofon stumm",
                  "▶️ Відновити прослуховування", "▶️ Resume Listening", "▶️ Zuhören fortsetzen"]:
        db.close()
        await voice_control_handler(update, context)
        return

    db.close()


async def voice_control_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Увімкнути/вимкнути голос та керування паузою"""
    tg_user = update.effective_user
    message = update.message
    if tg_user is None or message is None:
        return

    text = message.text
    user_id = tg_user.id

    if text in ["🎤 Увімкнути голос", "🎤 Enable Voice", "🎤 Stimme aktivieren"]:
        started = voice_daemon_manager.start_for_user(user_id)
        if started:
            await message.reply_text("✅ Голосовий режим увімкнено на пристрої")
        else:
            await message.reply_text("ℹ️ Голосовий режим вже працює")
        
    elif text in ["🔇 Заглушити мікрофон", "🔇 Mute Microphone", "🔇 Mikrofon stumm"]:
        # Призупиняємо прослуховування (daemon залишається запущеним)
        if voice_daemon_manager.is_running(user_id):
            paused = voice_daemon_manager.pause_for_user(user_id)
            if paused:
                await message.reply_text("🔇 Мікрофон заглушено (daemon працює)")
            else:
                await message.reply_text("ℹ️ Помилка заглушення")
        else:
            await message.reply_text("ℹ️ Голосовий режим не запущений")
    
    elif text in ["▶️ Відновити прослуховування", "▶️ Resume Listening", "▶️ Zuhören fortsetzen"]:
        # Відновлення прослуховування
        if voice_daemon_manager.is_running(user_id):
            resumed = voice_daemon_manager.resume_for_user(user_id)
            if resumed:
                await message.reply_text("▶️ Прослуховування відновлено")
            else:
                await message.reply_text("ℹ️ Помилка відновлення")
        else:
            await message.reply_text("ℹ️ Спочатку увімкніть голосовий режим")

async def openai_key_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка введення OpenAI API ключа"""
    user_data = getattr(context, "user_data", None)
    if not (isinstance(user_data, dict) and user_data.get("awaiting_openai_key")):
        return

    tg_user = update.effective_user
    message = update.message

    if tg_user is None or message is None:
        return

    user_id = tg_user.id
    api_key = (message.text or "").strip()

    db = SessionLocal()
    user = db.query(User).filter(User.telegram_user_id == user_id).first()
    db.close()

    if not user:
        return

    # Перевіряємо формат ключа (OpenAI або Groq)
    is_openai = api_key.startswith("sk-")
    is_groq = api_key.startswith("gsk_")
    
    if not is_openai and not is_groq:
        if user.language == "uk":
            await message.reply_text(
                "❌ Невірний формат ключа!\n\n"
                "Ключ повинен починатися з:\n"
                "• `sk-` (OpenAI)\n"
                "• `gsk_` (Groq - 5x швидше!)\n\n"
                "Спробуй ще раз:",
                parse_mode="Markdown",
            )
        else:
            await message.reply_text(
                "❌ Invalid key format!\n\n"
                "Key should start with:\n"
                "• `sk-` (OpenAI)\n"
                "• `gsk_` (Groq - 5x faster!)\n\n"
                "Try again:",
                parse_mode="Markdown",
            )
        return

    # Тестуємо ключ
    if user.language == "uk":
        await message.reply_text("🔄 Перевіряю ключ...")
    else:
        await message.reply_text("🔄 Validating key...")

    is_valid, validation_message = api_manager.validate_openai_key(api_key)

    if is_valid:
        # Зберігаємо ключ
        api_manager.set_openai_key(user_id, api_key)

        if user.language == "uk":
            await message.reply_text(
                "✅ OpenAI API ключ збережено!\n\n"
                "Тепер VoiceBot використовуватиме твій особистий ключ.",
                reply_markup=setup_menu_keyboard(user.language),
            )
        else:
            await message.reply_text(
                "✅ OpenAI API key saved!\n\n" "VoiceBot will now use your personal key.",
                reply_markup=setup_menu_keyboard(user.language),
            )
    else:
        await message.reply_text(validation_message, reply_markup=api_keys_keyboard(user.language))

    if isinstance(user_data, dict):
        user_data["awaiting_openai_key"] = False


# Spotify code handler видалено - Mopidy не потребує токенів від користувачів


async def google_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка Google Calendar токена (спрощений варіант)"""
    user_data = getattr(context, "user_data", None)
    if not (isinstance(user_data, dict) and user_data.get('awaiting_google_code')):
        return

    tg_user = update.effective_user
    message = update.message
    if tg_user is None or message is None:
        return

    user_id = tg_user.id
    token = (message.text or "").strip()

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
    finally:
        db.close()

    if not user:
        return

    await message.reply_text("🔄 Перевіряю токен..." if user.language == "uk" else "🔄 Checking token...")
    
    # Використовуємо простий метод (тільки access token)
    success, msg = google_calendar_manager.save_token_simple(user_id, token)
    await message.reply_text(msg)

    user_data['awaiting_google_code'] = False


async def personality_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Збереження/редагування промпту особистості з покращеною обробкою помилок"""
    user_data = getattr(context, "user_data", None)
    if not (isinstance(user_data, dict) and user_data.get('awaiting_personality')):
        return

    tg_user = update.effective_user
    message = update.message
    if tg_user is None or message is None:
        return

    user_id = tg_user.id
    text = (message.text or "").strip()

    print(f"Обробляю personality prompt для користувача {user_id}")
    print(f"Текст промту: '{text[:30]}...'")

    db = SessionLocal()
    user = None
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()

        if not user:
            await message.reply_text("❌ Помилка: користувача не знайдено в базі даних")
            return

        # Команди
        if text.lower() in ['переглянути', 'view']:
            current = user.personality_prompt or "Не встановлено"
            print(f"Поточний промт користувача: {current[:30]}...")
            await message.reply_text(
                f"🗣️ Поточний промпт:\n\n`{current}`",
                parse_mode='Markdown'
            )
            return

        elif text.lower() in ['скинути', 'reset']:
            try:
                user.personality_prompt = None
                db.commit()
                print("Промт успішно скинуто")
                await message.reply_text(
                    "✅ Промпт видалено. Бот використовуватиме стандартну поведінку.",
                    reply_markup=setup_menu_keyboard(user.language)
                )
                user_data['awaiting_personality'] = False
                return
            except Exception as e:
                print(f"❌ Помилка при скиданні промту: {e}")
                db.rollback()
                await message.reply_text(
                    "❌ Помилка при видаленні промпту. Спробуйте ще раз пізніше.",
                    reply_markup=setup_menu_keyboard(user.language)
                )
                user_data['awaiting_personality'] = False
                return

        # Новий промпт
        try:
            # Збережемо промт у 2 етапи з явною перевіркою
            # 1. Збереження в об'єкті моделі
            user.personality_prompt = text
            
            # 2. Явний commit в БД
            db.commit()
            
            # 3. Перевірка що промт справді зберігся
            db.refresh(user)
            saved_prompt = user.personality_prompt
            
            if saved_prompt == text:
                print("✅ Промт успішно збережено")
                success = True
            else:
                print("⚠️ Промт не збережено або збережено неправильно")
                success = False
                
        except Exception as e:
            print(f"❌ Помилка при збереженні промту: {e}")
            db.rollback()
            success = False

        if success:
            if user.language == "uk":
                await message.reply_text(
                    f"✅ Особистість оновлено!\n\n"
                    f"Новий промпт:\n`{text[:100]}{'...' if len(text) > 100 else ''}`",
                    parse_mode='Markdown',
                    reply_markup=setup_menu_keyboard(user.language)
                )
            else:
                await message.reply_text(
                    f"✅ Personality updated!\n\n"
                    f"New prompt:\n`{text[:100]}{'...' if len(text) > 100 else ''}`",
                    parse_mode='Markdown',
                    reply_markup=setup_menu_keyboard(user.language)
                )
        else:
            if user.language == "uk":
                await message.reply_text(
                    "❌ Помилка збереження промпту. Спробуйте скоротити текст або використати лише латинські символи.",
                    reply_markup=setup_menu_keyboard(user.language)
                )
            else:
                await message.reply_text(
                    "❌ Failed to save the prompt. Please try shortening the text or using only Latin characters.",
                    reply_markup=setup_menu_keyboard(user.language)
                )

        user_data['awaiting_personality'] = False
        
    except Exception as e:
        print(f"❌ Неочікувана помилка в personality_handler: {e}")
        await message.reply_text(
            "❌ Сталася неочікувана помилка. Спробуйте пізніше.",
            reply_markup=setup_menu_keyboard(user.language if user else "uk")
        )
        user_data['awaiting_personality'] = False
    finally:
        db.close()


async def music_control_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник керування музикою"""
    tg_user = update.effective_user
    message = update.message
    
    if tg_user is None or message is None:
        return
        
    user_id = tg_user.id
    text = message.text or ""
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        if not user:
            await message.reply_text("❌ Користувач не знайдений")
            return
            
        lang = user.language
        
        # Показуємо меню керування музикою
        if text in ["🎵 Керування музикою", "🎵 Musiksteuerung", "🎵 Music Control"]:
            # Перевіряємо чи грає музика
            state = mopidy_manager.get_playback_state()
            current = mopidy_manager.get_current_track()
            
            status_text = ""
            if state == "playing" and current:
                track_name = current.get("name", "Unknown")
                artists = current.get("artists", [])
                artist_name = artists[0].get("name", "Unknown") if artists else "Unknown"
                
                if lang == "uk":
                    status_text = f"▶️ Зараз грає:\n🎵 {track_name} - {artist_name}\n\n"
                elif lang == "de":
                    status_text = f"▶️ Läuft gerade:\n🎵 {track_name} - {artist_name}\n\n"
                else:
                    status_text = f"▶️ Now playing:\n🎵 {track_name} - {artist_name}\n\n"
            elif state == "paused":
                if lang == "uk":
                    status_text = "⏸️ Музика на паузі\n\n"
                elif lang == "de":
                    status_text = "⏸️ Musik pausiert\n\n"
                else:
                    status_text = "⏸️ Music paused\n\n"
            else:
                if lang == "uk":
                    status_text = "⏹️ Музика не грає\n\n"
                elif lang == "de":
                    status_text = "⏹️ Keine Musik\n\n"
                else:
                    status_text = "⏹️ No music playing\n\n"
            
            menu_text = status_text
            if lang == "uk":
                menu_text += "Оберіть дію:"
            elif lang == "de":
                menu_text += "Wähle eine Aktion:"
            else:
                menu_text += "Choose action:"
                
            await message.reply_text(
                menu_text,
                reply_markup=music_control_keyboard(lang)
            )
            return
            
        # Пауза
        if text in ["⏸️ Пауза", "⏸️ Pause"]:
            success, msg = mopidy_manager.pause()
            await message.reply_text(msg)
            
        # Продовжити
        elif text in ["▶️ Продовжити", "▶️ Fortsetzen", "▶️ Resume"]:
            success, msg = mopidy_manager.resume()
            await message.reply_text(msg)
            
        # Наступна
        elif text in ["⏭️ Наступна", "⏭️ Nächste", "⏭️ Next"]:
            success, msg = mopidy_manager.next_track()
            await message.reply_text(msg)
            
        # Попередня
        elif text in ["⏮️ Попередня", "⏮️ Vorherige", "⏮️ Previous"]:
            success, msg = mopidy_manager.previous_track()
            await message.reply_text(msg)
            
        # Зупинити з дотепним коментарем
        elif text in ["⏹️ Зупинити музику", "⏹️ Musik stoppen", "⏹️ Stop Music"]:
            success, msg = mopidy_manager.stop()
            
            # Дотепні коментарі
            if lang == "uk":
                comments = [
                    "⏹️ Зупинено! Нарешті тиша... 😌",
                    "⏹️ Музика зупинена. Мої вушка відпочивають! 🎧",
                    "⏹️ Тишаaa... Можна почути як думки літають 🦋",
                    "⏹️ Зупинено! Час для серйозних справ 🧐",
                    "⏹️ Музика OFF. Тепер я тут головний! 😎"
                ]
            elif lang == "de":
                comments = [
                    "⏹️ Gestoppt! Endlich Ruhe... 😌",
                    "⏹️ Musik gestoppt. Meine Ohren ruhen! 🎧",
                    "⏹️ Stille... Man kann die Gedanken fliegen hören 🦋",
                    "⏹️ Gestoppt! Zeit für ernste Dinge 🧐",
                    "⏹️ Musik AUS. Jetzt bin ich der Chef! 😎"
                ]
            else:
                comments = [
                    "⏹️ Stopped! Finally some peace... 😌",
                    "⏹️ Music stopped. My ears are resting! 🎧",
                    "⏹️ Silence... You can hear thoughts flying 🦋",
                    "⏹️ Stopped! Time for serious business 🧐",
                    "⏹️ Music OFF. Now I'm the boss here! 😎"
                ]
            
            funny_msg = random.choice(comments)
            await message.reply_text(funny_msg)
            
            # Сповіщаємо голосового бота що може слухати
            try:
                from core.tts import text_to_speech
                # Відправляємо коротке голосове повідомлення
                if lang == "uk":
                    voice_msg = "Музику зупинено. Я слухаю!"
                elif lang == "de":
                    voice_msg = "Musik gestoppt. Ich höre!"
                else:
                    voice_msg = "Music stopped. I'm listening!"
                    
                audio_data = text_to_speech(user_id, voice_msg)
                if audio_data:
                    # Відправляємо голосове повідомлення в чат
                    from io import BytesIO
                    audio_file = BytesIO(audio_data)
                    audio_file.name = "response.mp3"
                    await message.reply_voice(audio_file)
            except Exception as e:
                print(f"⚠️ Не вдалося відправити голосове: {e}")
            
        # Назад
        elif text in ["🔙 Назад", "🔙 Zurück", "🔙 Back"]:
            await message.reply_text(
                "🏠 Головне меню" if lang == "uk" else ("🏠 Hauptmenü" if lang == "de" else "🏠 Main menu"),
                reply_markup=main_menu_keyboard(lang)
            )
            
    finally:
        db.close()


async def timer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник таймерів"""
    tg_user = update.effective_user
    message = update.message
    
    if tg_user is None or message is None:
        return
        
    user_id = tg_user.id
    text = message.text or ""
    user_data = getattr(context, "user_data", {})
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        if not user:
            await message.reply_text("❌ Користувач не знайдений")
            return
            
        lang = user.language
        
        # Показуємо інструкцію
        if text in ["⏰ Таймер", "⏰ Timer"]:
            if lang == "uk":
                await message.reply_text(
                    "⏰ Встановлення таймера\n\n"
                    "Надішли час у хвилинах, наприклад:\n"
                    "• `5` - таймер на 5 хвилин\n"
                    "• `10` - таймер на 10 хвилин\n"
                    "• `30` - таймер на 30 хвилин\n\n"
                    "Або скажи голосом:\n"
                    "• 'Встанов таймер на 5 хвилин'\n"
                    "• 'Нагадай через 10 хвилин'",
                    parse_mode='Markdown',
                    reply_markup=main_menu_keyboard(lang)
                )
            elif lang == "de":
                await message.reply_text(
                    "⏰ Timer einstellen\n\n"
                    "Sende die Zeit in Minuten, z.B.:\n"
                    "• `5` - Timer für 5 Minuten\n"
                    "• `10` - Timer für 10 Minuten\n"
                    "• `30` - Timer für 30 Minuten\n\n"
                    "Oder sage mit Stimme:\n"
                    "• 'Stelle Timer für 5 Minuten'\n"
                    "• 'Erinnere in 10 Minuten'",
                    parse_mode='Markdown',
                    reply_markup=main_menu_keyboard(lang)
                )
            else:
                await message.reply_text(
                    "⏰ Set Timer\n\n"
                    "Send time in minutes, e.g.:\n"
                    "• `5` - timer for 5 minutes\n"
                    "• `10` - timer for 10 minutes\n"
                    "• `30` - timer for 30 minutes\n\n"
                    "Or say by voice:\n"
                    "• 'Set timer for 5 minutes'\n"
                    "• 'Remind in 10 minutes'",
                    parse_mode='Markdown',
                    reply_markup=main_menu_keyboard(lang)
                )
            user_data['awaiting_timer'] = True
            return
            
        # Обробляємо введений час
        if user_data.get('awaiting_timer'):
            try:
                minutes = int(text)
                if minutes <= 0 or minutes > 1440:  # Максимум 24 години
                    if lang == "uk":
                        await message.reply_text("❌ Час має бути від 1 до 1440 хвилин (24 години)")
                    elif lang == "de":
                        await message.reply_text("❌ Zeit muss zwischen 1 und 1440 Minuten (24 Stunden) sein")
                    else:
                        await message.reply_text("❌ Time must be between 1 and 1440 minutes (24 hours)")
                    return
                    
                # Встановлюємо таймер
                from datetime import datetime, timedelta
                
                end_time = datetime.now() + timedelta(minutes=minutes)
                
                # Зберігаємо таймер у context.job_queue
                if hasattr(context, 'job_queue') and context.job_queue:
                    # Callback для спрацювання таймера
                    async def timer_callback(ctx):
                        try:
                            from core.tts import text_to_speech
                            
                            if lang == "uk":
                                text_msg = f"⏰ Таймер на {minutes} хв спрацював!"
                                voice_msg = f"Таймер на {minutes} хвилин спрацював!"
                            elif lang == "de":
                                text_msg = f"⏰ Timer für {minutes} Min ist abgelaufen!"
                                voice_msg = f"Timer für {minutes} Minuten ist abgelaufen!"
                            else:
                                text_msg = f"⏰ Timer for {minutes} min is up!"
                                voice_msg = f"Timer for {minutes} minutes is up!"
                            
                            # Текстове повідомлення
                            await ctx.bot.send_message(
                                chat_id=user_id,
                                text=text_msg
                            )
                            
                            # Голосове повідомлення
                            try:
                                audio_data = text_to_speech(user_id, voice_msg)
                                if audio_data:
                                    from io import BytesIO
                                    audio_file = BytesIO(audio_data)
                                    audio_file.name = "timer.mp3"
                                    await ctx.bot.send_voice(
                                        chat_id=user_id,
                                        voice=audio_file
                                    )
                            except Exception as e:
                                print(f"⚠️ Помилка відправки голосового таймера: {e}")
                                
                        except Exception as e:
                            print(f"❌ Помилка в timer_callback: {e}")
                    
                    # Додаємо job
                    context.job_queue.run_once(
                        timer_callback,
                        when=minutes * 60,  # в секундах
                        name=f"timer_{user_id}_{minutes}",
                        chat_id=user_id
                    )
                    
                    if lang == "uk":
                        await message.reply_text(
                            f"✅ Таймер встановлено на {minutes} хв\n"
                            f"⏰ Спрацює о {end_time.strftime('%H:%M')}",
                            reply_markup=main_menu_keyboard(lang)
                        )
                    elif lang == "de":
                        await message.reply_text(
                            f"✅ Timer gestellt für {minutes} Min\n"
                            f"⏰ Klingelt um {end_time.strftime('%H:%M')}",
                            reply_markup=main_menu_keyboard(lang)
                        )
                    else:
                        await message.reply_text(
                            f"✅ Timer set for {minutes} min\n"
                            f"⏰ Will ring at {end_time.strftime('%H:%M')}",
                            reply_markup=main_menu_keyboard(lang)
                        )
                else:
                    await message.reply_text("❌ Job queue not available")
                    
            except ValueError:
                if lang == "uk":
                    await message.reply_text("❌ Будь ласка, введіть число (кількість хвилин)")
                elif lang == "de":
                    await message.reply_text("❌ Bitte geben Sie eine Zahl ein (Anzahl Minuten)")
                else:
                    await message.reply_text("❌ Please enter a number (minutes)")
                return
                
            user_data['awaiting_timer'] = False
            
    finally:
        db.close()


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник історії розмов"""
    tg_user = update.effective_user
    message = update.message
    
    if tg_user is None or message is None:
        return
        
    user_id = tg_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        if not user:
            await message.reply_text("❌ Користувач не знайдений")
            return
            
        lang = user.language
        
        # Отримуємо історію з БД
        from storage.models import Conversation
        
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).order_by(Conversation.timestamp.desc()).limit(10).all()
        
        if not conversations:
            if lang == "uk":
                text = "📜 Історія розмов порожня\n\nПочніть спілкуватися з ботом голосом!"
            elif lang == "de":
                text = "📜 Gesprächsverlauf ist leer\n\nBeginnen Sie per Sprache mit dem Bot zu kommunizieren!"
            else:
                text = "📜 Conversation history is empty\n\nStart talking to the bot by voice!"
            
            await message.reply_text(text, reply_markup=main_menu_keyboard(lang))
            return
        
        # Форматуємо історію
        if lang == "uk":
            text = "📜 Історія останніх 10 команд:\n\n"
        elif lang == "de":
            text = "📜 Verlauf der letzten 10 Befehle:\n\n"
        else:
            text = "📜 History of last 10 commands:\n\n"
        
        for i, conv in enumerate(reversed(conversations), 1):
            time_str = conv.timestamp.strftime("%d.%m %H:%M")
            cmd = conv.command[:40] + "..." if len(conv.command) > 40 else conv.command
            resp = conv.response[:60] + "..." if len(conv.response) > 60 else conv.response
            text += f"{i}. [{time_str}]\n"
            text += f"   ❓ {cmd}\n"
            text += f"   ✅ {resp}\n\n"
        
        await message.reply_text(text, reply_markup=main_menu_keyboard(lang))
        
    finally:
        db.close()


async def fun_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник розваг (жарти/факти)"""
    tg_user = update.effective_user
    message = update.message
    
    if tg_user is None or message is None:
        return
        
    user_id = tg_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_user_id == user_id).first()
        if not user:
            await message.reply_text("❌ Користувач не знайдений")
            return
            
        lang = user.language
        
        # Випадково обираємо жарт або факт
        from integrations.fun import fun_manager
        
        success, message_text = fun_manager.get_random_fun(lang)
        
        await message.reply_text(message_text, reply_markup=main_menu_keyboard(lang))
        
    finally:
        db.close()