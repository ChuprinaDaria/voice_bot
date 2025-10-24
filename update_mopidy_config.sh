#!/bin/bash

echo "🔄 Оновлюю конфіг Mopidy для ReSpeaker..."

# Створюємо новий конфіг
cat > /tmp/mopidy_new.conf << 'EOF'
[core]
cache_dir = /var/cache/mopidy
config_dir = /etc/mopidy
data_dir = /var/lib/mopidy

[audio]
output = alsasink device=plughw:3,0 buffer-time=200000

[http]
enabled = true
hostname = 127.0.0.1
port = 6680

[youtube]
enabled = true
youtube_dl_package = yt_dlp
musicapi_enabled = false
EOF

# Копіюємо новий конфіг
sudo cp /tmp/mopidy_new.conf /etc/mopidy/mopidy.conf

# Перезапускаємо Mopidy
sudo systemctl restart mopidy

echo "✅ Mopidy оновлено для ReSpeaker!"
echo "🎵 Тепер музика буде грати через ReSpeaker"
