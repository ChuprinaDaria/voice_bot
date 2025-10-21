from __future__ import annotations

from datetime import datetime
import re

from telegram import Update
from telegram.ext import ContextTypes

from storage.database import SessionLocal
from storage.models import ActivationCode, User
from .keyboards import main_menu_keyboard, setup_menu_keyboard, api_keys_keyboard, language_keyboard, voice_control_keyboard
from core.state_manager import voice_daemon_manager
from core.api_manager import api_manager
from integrations.spotify import spotify_manager
from integrations.google_calendar import google_calendar_manager


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

    # Почати розмову (локально на пристрої) — підтримка без емодзі/англ
    normalized = (text or "").strip().lower().replace("🎙️", "").strip()
    if normalized in ["почати розмову", "start conversation"]:
        started = voice_daemon_manager.start_for_user(user_id, listen_immediately=True)
        if started:
            await message.reply_text("✅ Режим розмови запущено на пристрої")
        else:
            await message.reply_text("ℹ️ Режим вже запущений")
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

    # OpenAI API Key
    elif text in ["🔑 OpenAI API Key"]:
        if user.language == "uk":
            text_msg = (
                "🔑 OpenAI API Key\n\n"
                "Надішли свій ключ API у форматі:\n"
                "`sk-proj-xxxxxxxxxxxxx`\n\n"
                "📖 Де взяти ключ?\n"
                "1. Іди на https://platform.openai.com\n"
                "2. Account → API Keys\n"
                "3. Create new secret key\n"
                "4. Скопіюй і надішли сюди\n\n"
                "⚠️ Ключ зберігається зашифрованим"
            )
        else:
            text_msg = (
                "🔑 OpenAI API Key\n\n"
                "Send your API key in format:\n"
                "`sk-proj-xxxxxxxxxxxxx`\n\n"
                "📖 Where to get the key?\n"
                "1. Go to https://platform.openai.com\n"
                "2. Account → API Keys\n"
                "3. Create new secret key\n"
                "4. Copy and send here\n\n"
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
    elif text in ["🎵 Spotify", "🎵 Підключити Spotify", "🎵 Connect Spotify"]:
        if spotify_manager.is_connected(user_id):
            if user.language == "uk":
                await message.reply_text(
                    "✅ Spotify вже підключено!\n\n"
                    "Щоб відтворити пісню, надішли:\n"
                    "`Грай: Назва пісні`",
                    parse_mode='Markdown'
                )
            else:
                await message.reply_text(
                    "✅ Spotify already connected!\n\n"
                    "To play a song, send:\n"
                    "`Play: Song name`",
                    parse_mode='Markdown'
                )
        else:
            auth_url = spotify_manager.get_auth_url(user_id)
            if user.language == "uk":
                text_msg = (
                    "🎵 Підключення Spotify\n\n"
                    "📖 Інструкція:\n"
                    "1. Натисни на посилання нижче\n"
                    "2. Авторизуйся в Spotify\n"
                    "3. Скопіюй код який отримаєш\n"
                    "4. Надішли його сюди\n\n"
                    f"🔗 [Авторизуватися]({auth_url})"
                )
            else:
                text_msg = (
                    "🎵 Connect Spotify\n\n"
                    "📖 Instructions:\n"
                    "1. Click link below\n"
                    "2. Authorize in Spotify\n"
                    "3. Copy the code you receive\n"
                    "4. Send it here\n\n"
                    f"🔗 [Authorize]({auth_url})"
                )

            await message.reply_text(
                text_msg,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            user_data = getattr(context, "user_data", None)
            if isinstance(user_data, dict):
                user_data['awaiting_spotify_code'] = True

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
            auth_url = google_calendar_manager.get_auth_url(user_id)
            if user.language == "uk":
                text_msg = (
                    "📅 Підключення Google Calendar\n\n"
                    "📖 Інструкція:\n"
                    "1. Натисни на посилання\n"
                    "2. Авторизуйся в Google\n"
                    "3. Скопіюй код\n"
                    "4. Надішли його сюди\n\n"
                    f"🔗 [Авторизуватися]({auth_url})"
                )
            else:
                text_msg = (
                    "📅 Connect Google Calendar\n\n"
                    "📖 Instructions:\n"
                    "1. Click link\n"
                    "2. Authorize in Google\n"
                    "3. Copy code\n"
                    "4. Send it here\n\n"
                    f"🔗 [Authorize]({auth_url})"
                )

            await message.reply_text(
                text_msg,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            user_data = getattr(context, "user_data", None)
            if isinstance(user_data, dict):
                user_data['awaiting_google_code'] = True

    # Особистість - РЕДАГУВАННЯ
    elif text in ["🗣️ Особистість", "🗣️ Налаштувати особистість", "🗣️ Setup Personality"]:
        current_prompt = user.personality_prompt or "Не встановлено"

        if user.language == "uk":
            text_msg = (
                "🗣️ Особистість бота\n\n"
                f"Поточний промпт:\n`{current_prompt}`\n\n"
                "Надішли новий промпт або команди:\n"
                "• `переглянути` - показати поточний\n"
                "• `скинути` - видалити промпт\n"
                "• або надішли новий текст"
            )
        else:
            text_msg = (
                "🗣️ Bot Personality\n\n"
                f"Current prompt:\n`{current_prompt}`\n\n"
                "Send new prompt or commands:\n"
                "• `view` - show current\n"
                "• `reset` - delete prompt\n"
                "• or send new text"
            )

        await message.reply_text(text_msg, parse_mode='Markdown')
        user_data = getattr(context, "user_data", None)
        if isinstance(user_data, dict):
            user_data['awaiting_personality'] = True
    
    # Швидке збереження промпту без входу в стан: "Промпт: ..." / "Prompt: ..."
    elif isinstance(text, str) and (text.lower().startswith("промпт:") or text.lower().startswith("prompt:")):
        new_prompt = text.split(":", 1)[1].strip() if (":" in text) else ""
        if not new_prompt:
            await message.reply_text(
                "❌ Не вдалося розпізнати текст після 'Промпт:'" if user.language == "uk" else "❌ No text after 'Prompt:'"
            )
            db.close()
            return
        user.personality_prompt = new_prompt
        db.commit()
        await message.reply_text(
            ("✅ Особистість оновлено!" if user.language == "uk" else "✅ Personality updated!"),
            reply_markup=setup_menu_keyboard(user.language)
        )
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
            reply_markup=main_menu_keyboard(),
        )

    db.close()


async def voice_control_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Увімкнути/вимкнути голос"""
    tg_user = update.effective_user
    message = update.message
    if tg_user is None or message is None:
        return

    text = message.text
    user_id = tg_user.id

    if text in ["🎤 Увімкнути голос", "🎤 Enable Voice"]:
        started = voice_daemon_manager.start_for_user(user_id)
        if started:
            await message.reply_text("✅ Голосовий режим увімкнено на пристрої")
        else:
            await message.reply_text("ℹ️ Голосовий режим вже працює")
        
    elif text in ["🔇 Вимкнути голос", "🔇 Disable Voice"]:
        stopped = voice_daemon_manager.stop_for_user(user_id)
        if stopped:
            await message.reply_text("🔇 Голосовий режим вимкнено")
        else:
            await message.reply_text("ℹ️ Голосовий режим вже вимкнений")

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

    # Перевіряємо формат ключа
    if not api_key.startswith("sk-"):
        if user.language == "uk":
            await message.reply_text(
                "❌ Невірний формат ключа.\n" "Ключ має починатися з `sk-`",
                parse_mode="Markdown",
            )
        else:
            await message.reply_text(
                "❌ Invalid key format.\n" "Key must start with `sk-`",
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


async def spotify_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка Spotify authorization code"""
    user_data = getattr(context, "user_data", None)
    if not (isinstance(user_data, dict) and user_data.get('awaiting_spotify_code')):
        return

    tg_user = update.effective_user
    message = update.message
    if tg_user is None or message is None:
        return

    user_id = tg_user.id
    code = (message.text or "").strip()

    await message.reply_text("🔄 Обробляю код...")
    await message.reply_text(
        "⚠️ Spotify OAuth потребує веб-сервер.\n"
        "Ця функція в розробці.\n\n"
        "Поки що використовуй голосові команди без Spotify."
    )

    user_data['awaiting_spotify_code'] = False


async def google_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка Google authorization code"""
    user_data = getattr(context, "user_data", None)
    if not (isinstance(user_data, dict) and user_data.get('awaiting_google_code')):
        return

    tg_user = update.effective_user
    message = update.message
    if tg_user is None or message is None:
        return

    user_id = tg_user.id
    code = (message.text or "").strip()

    await message.reply_text("🔄 Обробляю код...")
    await message.reply_text(
        "⚠️ Google OAuth потребує веб-сервер.\n"
        "Ця функція в розробці."
    )

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