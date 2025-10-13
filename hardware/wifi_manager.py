import subprocess
import os


class WiFiManager:
    """Керування WiFi на Raspberry Pi"""

    def __init__(self):
        self.wpa_config = "/etc/wpa_supplicant/wpa_supplicant.conf"

    def scan_networks(self):
        """Сканує доступні WiFi мережі"""
        try:
            result = subprocess.run(
                ["sudo", "iwlist", "wlan0", "scan"], capture_output=True, text=True
            )
            # Парсинг результатів (спрощено)
            networks = []
            for line in result.stdout.split('\n'):
                if 'ESSID:' in line:
                    ssid = line.split('ESSID:')[1].strip('"')
                    if ssid:
                        networks.append(ssid)
            return list(set(networks))  # Унікальні
        except Exception as e:
            print(f"❌ Помилка сканування: {e}")
            return []

    def connect_to_wifi(self, ssid: str, password: str):
        """Підключається до WiFi мережі"""
        try:
            # Створюємо конфігурацію
            config = f'''
network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
            # Додаємо в wpa_supplicant.conf
            with open("/tmp/wifi_temp.conf", "w") as f:
                f.write(config)

            # Копіюємо з правами root
            subprocess.run(
                ["sudo", "bash", "-c", f"cat /tmp/wifi_temp.conf >> {self.wpa_config}"],
                check=True,
            )

            # Перезавантажуємо WiFi
            subprocess.run(["sudo", "wpa_cli", "-i", "wlan0", "reconfigure"], check=True)

            # Чекаємо підключення
            import time

            time.sleep(5)

            # Перевіряємо чи підключились
            if self.is_connected():
                return True, "✅ Підключено до WiFi"
            else:
                return False, "❌ Не вдалося підключитись. Перевір пароль."

        except Exception as e:
            return False, f"❌ Помилка: {str(e)}"

    def is_connected(self):
        """Перевіряє чи є WiFi підключення"""
        try:
            result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
            return bool(result.stdout.strip())
        except Exception:
            return False

    def get_current_network(self):
        """Повертає назву поточної WiFi мережі"""
        try:
            result = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True)
            return result.stdout.strip() or "Не підключено"
        except Exception:
            return "Невідомо"

    def get_ip_address(self):
        """Повертає IP адресу"""
        try:
            result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
            return result.stdout.split()[0]
        except Exception:
            return "Невідомо"


# Глобальний об'єкт
wifi_manager = WiFiManager()


