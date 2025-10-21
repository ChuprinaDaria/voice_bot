# 🎵 Налаштування Mopidy для VoiceBot

Mopidy — це потужний музичний сервер для Raspberry Pi з підтримкою:
- ✅ Spotify
- ✅ YouTube Music
- ✅ Локальні MP3/FLAC файли
- ✅ HTTP API для керування

---

## 📦 Крок 1: Встановлення Mopidy

```bash
# Оновлюємо систему
sudo apt update

# Додаємо репозиторій Mopidy
sudo mkdir -p /usr/local/share/keyrings
wget -q -O /usr/local/share/keyrings/mopidy-archive-keyring.gpg https://apt.mopidy.com/mopidy.gpg
wget -q -O /etc/apt/sources.list.d/mopidy.list https://apt.mopidy.com/bullseye.list

# Встановлюємо Mopidy
sudo apt update
sudo apt install -y mopidy

# Встановлюємо плагіни
sudo apt install -y mopidy-spotify
pip3 install Mopidy-YouTube
```

---

## ⚙️ Крок 2: Налаштування

Створюємо конфіг:

```bash
sudo nano /etc/mopidy/mopidy.conf
```

Додаємо:

```ini
[core]
cache_dir = /var/cache/mopidy
config_dir = /etc/mopidy
data_dir = /var/lib/mopidy

[audio]
output = alsasink

[http]
enabled = true
hostname = 127.0.0.1
port = 6680

[spotify]
enabled = true
username = ТВІй_SPOTIFY_ЛОГІН
password = ТВІй_SPOTIFY_ПАРОЛЬ
client_id = ТВІй_CLIENT_ID
client_secret = ТВІй_CLIENT_SECRET

[youtube]
enabled = true
```

---

## 🚀 Крок 3: Запуск

```bash
# Запускаємо Mopidy
sudo systemctl start mopidy

# Додаємо в автозапуск
sudo systemctl enable mopidy

# Перевіряємо статус
sudo systemctl status mopidy

# Перевіряємо чи працює HTTP API
curl http://localhost:6680/mopidy/rpc -d '{"jsonrpc": "2.0", "id": 1, "method": "core.get_version"}'
```

Якщо все ОК, побачиш відповідь з версією Mopidy.

---

## 🎵 Крок 4: Тестування

```bash
# Пошук треку
curl http://localhost:6680/mopidy/rpc -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "core.library.search",
  "params": {
    "query": {"any": ["Imagine Dragons"]},
    "uris": ["spotify:"]
  }
}'

# Додати трек в плейлист і відтворити
curl http://localhost:6680/mopidy/rpc -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "core.tracklist.add",
  "params": {"uris": ["spotify:track:URI_ТРЕКУ"]}
}'

curl http://localhost:6680/mopidy/rpc -d '{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "core.playback.play"
}'
```

---

## 📝 Логи (для діагностики)

```bash
# Дивимось логи Mopidy
sudo journalctl -u mopidy -f

# Перезапуск після зміни конфігу
sudo systemctl restart mopidy
```

---

## ✅ Готово!

Тепер VoiceBot може керувати музикою через HTTP API без OAuth заморочок! 🎉

