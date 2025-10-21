from __future__ import annotations

from typing import Dict, Any, Tuple, List


SUPPORTED_LANGUAGES: Dict[str, str] = {
    "uk": "Українська",
    "en": "English",
    "de": "Deutsch",
}


TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "uk": {
        "settings_menu": "⚙️ Меню налаштувань:",
        "language_updated": "✅ Мову змінено",
        "back_to_settings": "🔙 Назад до налаштувань",
        "choose_language": "Оберіть мову:",
        "start_conversation": "🎙️ Почати розмову",
        "conversation_started": "✅ Режим розмови запущено на пристрої",
        "conversation_already_started": "ℹ️ Режим вже запущений",
        "voice_menu": "Керування голосом",
        "voice_enabled": "✅ Голосовий режим увімкнено на пристрої",
        "voice_already_enabled": "ℹ️ Голосовий режим вже працює",
        "voice_disabled": "🔇 Голосовий режим вимкнено",
        "voice_already_disabled": "ℹ️ Голосовий режим вже вимкнений",
        "enable_voice": "🎤 Увімкнути голос",
        "disable_voice": "🔇 Вимкнути голос",
        "api_keys_menu": "🔑 Керування API ключами",
        "openai_key_set": "✅ Встановлено: {}",
        "openai_key_default": "⚠️ Використовується системний ключ",
        "choose_action": "Оберіть дію:",
        "openai_key_validation": "🔄 Перевіряю ключ...",
        "openai_key_saved": "✅ OpenAI API ключ збережено!\n\nТепер VoiceBot використовуватиме твій особистий ключ.",
        "openai_key_invalid_format": "❌ Невірний формат ключа.\nКлюч має починатися з `sk-`",
        "personality_menu": "🗣️ Налаштувати особистість",
        "personality_prompt": "🗣️ Особистість бота",
        "current_prompt": "Поточний промпт:\n`{}`",
        "prompt_not_set": "Не встановлено",
        "personality_updated": "✅ Особистість оновлено!",
        "personality_reset": "✅ Промпт видалено. Бот використовуватиме стандартну поведінку.",
        "personality_save_error": "❌ Помилка збереження промпту. Спробуйте пізніше або скоротіть текст.",
        "new_prompt": "Новий промпт:\n`{}`",
        "prompt_commands": "Надішли новий промпт або команди:\n• `переглянути` - показати поточний\n• `скинути` - видалити промпт\n• або надішли новий текст",
        "activate_first": "❌ Спочатку активуй пристрій.\nВведи код активації з коробки.",
        "settings": "⚙️ Налаштування",
        "main_menu": "Головне меню",
        "finish_setup": "✅ Завершити налаштування",
    },
    "en": {
        "settings_menu": "⚙️ Settings menu:",
        "language_updated": "✅ Language updated",
        "back_to_settings": "🔙 Back to Settings",
        "choose_language": "Choose language:",
        "start_conversation": "🎙️ Start conversation",
        "conversation_started": "✅ Conversation mode started on device",
        "conversation_already_started": "ℹ️ Mode already running",
        "voice_menu": "Voice control",
        "voice_enabled": "✅ Voice mode enabled on device",
        "voice_already_enabled": "ℹ️ Voice mode already running",
        "voice_disabled": "🔇 Voice mode disabled",
        "voice_already_disabled": "ℹ️ Voice mode already disabled",
        "enable_voice": "🎤 Enable Voice",
        "disable_voice": "🔇 Disable Voice",
        "api_keys_menu": "🔑 API Keys Management",
        "openai_key_set": "✅ Set: {}",
        "openai_key_default": "⚠️ Using system key",
        "choose_action": "Choose action:",
        "openai_key_validation": "🔄 Validating key...",
        "openai_key_saved": "✅ OpenAI API key saved!\n\nVoiceBot will now use your personal key.",
        "openai_key_invalid_format": "❌ Invalid key format.\nKey must start with `sk-`",
        "personality_menu": "🗣️ Setup Personality",
        "personality_prompt": "🗣️ Bot Personality",
        "current_prompt": "Current prompt:\n`{}`",
        "prompt_not_set": "Not set",
        "personality_updated": "✅ Personality updated!",
        "personality_reset": "✅ Prompt deleted. Bot will use standard behavior.",
        "personality_save_error": "❌ Failed to save the prompt. Please try again later or shorten the text.",
        "new_prompt": "New prompt:\n`{}`",
        "prompt_commands": "Send new prompt or commands:\n• `view` - show current\n• `reset` - delete prompt\n• or send new text",
        "activate_first": "❌ Please activate your device first.\nEnter the activation code from the box.",
        "settings": "⚙️ Settings",
        "main_menu": "Main menu",
        "finish_setup": "✅ Finish Setup",
    },
    "de": {
        "settings_menu": "⚙️ Einstellungsmenü:",
        "language_updated": "✅ Sprache aktualisiert",
        "back_to_settings": "🔙 Zurück zu Einstellungen",
        "choose_language": "Sprache wählen:",
        "start_conversation": "🎙️ Gespräch starten",
        "conversation_started": "✅ Gesprächsmodus auf Gerät gestartet",
        "conversation_already_started": "ℹ️ Modus läuft bereits",
        "voice_menu": "Sprachsteuerung",
        "voice_enabled": "✅ Sprachmodus auf Gerät aktiviert",
        "voice_already_enabled": "ℹ️ Sprachmodus läuft bereits",
        "voice_disabled": "🔇 Sprachmodus deaktiviert",
        "voice_already_disabled": "ℹ️ Sprachmodus bereits deaktiviert",
        "enable_voice": "🎤 Stimme aktivieren",
        "disable_voice": "🔇 Stimme deaktivieren",
        "api_keys_menu": "🔑 API-Schlüsselverwaltung",
        "openai_key_set": "✅ Eingestellt: {}",
        "openai_key_default": "⚠️ Systemschlüssel wird verwendet",
        "choose_action": "Aktion wählen:",
        "openai_key_validation": "🔄 Schlüssel wird validiert...",
        "openai_key_saved": "✅ OpenAI API-Schlüssel gespeichert!\n\nVoiceBot verwendet jetzt Ihren persönlichen Schlüssel.",
        "openai_key_invalid_format": "❌ Ungültiges Schlüsselformat.\nDer Schlüssel muss mit `sk-` beginnen",
        "personality_menu": "🗣️ Persönlichkeit einrichten",
        "personality_prompt": "🗣️ Bot-Persönlichkeit",
        "current_prompt": "Aktueller Prompt:\n`{}`",
        "prompt_not_set": "Nicht eingestellt",
        "personality_updated": "✅ Persönlichkeit aktualisiert!",
        "personality_reset": "✅ Prompt gelöscht. Bot verwendet Standardverhalten.",
        "personality_save_error": "❌ Fehler beim Speichern des Prompts. Bitte versuchen Sie es später erneut oder kürzen Sie den Text.",
        "new_prompt": "Neuer Prompt:\n`{}`",
        "prompt_commands": "Neuen Prompt oder Befehle senden:\n• `view` - aktuellen anzeigen\n• `reset` - Prompt löschen\n• oder neuen Text senden",
        "activate_first": "❌ Bitte aktivieren Sie zuerst Ihr Gerät.\nGeben Sie den Aktivierungscode aus der Box ein.",
        "settings": "⚙️ Einstellungen",
        "main_menu": "Hauptmenü",
        "finish_setup": "✅ Einrichtung abschließen",
    },
}


def get_text(key: str, language: str = "uk", **kwargs: Any) -> str:
    if language not in TRANSLATIONS:
        language = "en"
    translations = TRANSLATIONS.get(language, TRANSLATIONS["en"])
    text = translations.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


def get_all_languages() -> List[Tuple[str, str]]:
    return [(code, name) for code, name in SUPPORTED_LANGUAGES.items()]


