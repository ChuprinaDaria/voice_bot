from __future__ import annotations

import threading
from typing import Dict

from voice_daemon import VoiceDaemon


class VoiceDaemonManager:
    """Керує життєвим циклом VoiceDaemon для користувачів.

    Створює/зупиняє тло потік з `VoiceDaemon.start()` для кожного telegram_user_id.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._user_id_to_thread: Dict[int, threading.Thread] = {}
        self._user_id_to_daemon: Dict[int, VoiceDaemon] = {}

    def start_for_user(self, telegram_user_id: int, listen_immediately: bool = False) -> bool:
        """Запускає VoiceDaemon у фоні для користувача. Повертає True, якщо запущено зараз.

        Args:
            telegram_user_id: ID користувача Telegram
            listen_immediately: Якщо True — одразу почати слухати без wake word
        """
        with self._lock:
            existing_thread = self._user_id_to_thread.get(telegram_user_id)
            if existing_thread and existing_thread.is_alive():
                return False

            daemon = VoiceDaemon(telegram_user_id)
            thread = threading.Thread(
                target=lambda: daemon.start(listen_immediately=listen_immediately),
                daemon=True,
            )

            self._user_id_to_daemon[telegram_user_id] = daemon
            self._user_id_to_thread[telegram_user_id] = thread

            thread.start()
            return True

    def stop_for_user(self, telegram_user_id: int) -> bool:
        """Зупиняє VoiceDaemon для користувача. Повертає True, якщо успішно зупинено."""
        with self._lock:
            daemon = self._user_id_to_daemon.get(telegram_user_id)
            thread = self._user_id_to_thread.get(telegram_user_id)

        if not daemon or not thread:
            return False

        try:
            daemon.stop()
        except Exception:
            # Безпечна зупинка навіть якщо вже зупинений
            pass

        thread.join(timeout=2.0)

        with self._lock:
            is_alive = thread.is_alive()
            if not is_alive:
                self._user_id_to_thread.pop(telegram_user_id, None)
                self._user_id_to_daemon.pop(telegram_user_id, None)
            return not is_alive

    def is_running(self, telegram_user_id: int) -> bool:
        """Перевіряє, чи працює VoiceDaemon для користувача."""
        with self._lock:
            thread = self._user_id_to_thread.get(telegram_user_id)
            return bool(thread and thread.is_alive())


# Глобальний менеджер
voice_daemon_manager = VoiceDaemonManager()


