# 🚀 Опції оптимізації VoiceBot для Raspberry Pi 5

## 1. Локальна LLM замість OpenAI

### Варіант А: Ollama (НАЙПРОСТІШИЙ)
```bash
# Встановлення
curl -fsSL https://ollama.com/install.sh | sh

# Завантаження легкої моделі
ollama pull phi3:mini        # 2.3GB, швидка
ollama pull tinyllama        # 637MB, дуже швидка
ollama pull gemma:2b         # 1.4GB, якісна

# Використання
ollama run phi3:mini "Привіт, як справи?"
```

**Інтеграція:**
```python
# core/llm_local.py
import requests

def ask_ollama(prompt: str, model: str = "phi3:mini") -> str:
    response = requests.post('http://localhost:11434/api/generate', 
        json={
            "model": model,
            "prompt": prompt,
            "stream": False
        })
    return response.json()['response']
```

**Швидкість:** 0.5-2 секунди (залежно від моделі)
**Переваги:** Працює офлайн, безкоштовно
**Мінуси:** Якість нижча ніж GPT-3.5

---

### Варіант Б: llama.cpp (НАЙШВИДШИЙ)
```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make

# Завантажити GGUF модель (наприклад TinyLlama)
wget https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

# Запустити сервер
./server -m tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf -c 2048 --host 0.0.0.0 --port 8080
```

**Швидкість:** 0.3-1 секунда
**RAM:** 1-3GB

---

### Варіант В: OpenAI-сумісний API (Groq / Together.ai)

**Groq (РЕКОМЕНДУЮ - НАЙШВИДШИЙ):**
```python
from openai import OpenAI

client = OpenAI(
    api_key="your-groq-api-key",
    base_url="https://api.groq.com/openai/v1"
)

response = client.chat.completions.create(
    model="llama3-8b-8192",  # Або "mixtral-8x7b-32768"
    messages=[...],
    max_tokens=80
)
```

**Швидкість:** 0.5-1.5 секунди (НАБАГАТО швидше ніж OpenAI!)
**Безкоштовно:** 30 requests/min
**Якість:** Як GPT-3.5 або краще

**Реєстрація:** https://console.groq.com/

---

## 2. Прискорення STT (Whisper)

### Варіант А: Локальний Whisper (faster-whisper)
```bash
pip install faster-whisper
```

```python
from faster_whisper import WhisperModel

model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe(audio_file, language="uk")
text = " ".join([segment.text for segment in segments])
```

**Швидкість:** 1-3 секунди (замість 3-6 через API)
**Модель:** base (74MB) або small (244MB)

### Варіант Б: Vosk (ОФЛАЙН)
```bash
pip install vosk
wget https://alphacephei.com/vosk/models/vosk-model-uk-v3.zip
unzip vosk-model-uk-v3.zip
```

**Швидкість:** 0.5-1 секунда (ДУЖЕ ШВИДКО!)
**Мінус:** Гірша якість ніж Whisper

---

## 3. Заміна голосу TTS

### Варіант А: OpenAI TTS (НАЙЯКІСНІШИЙ)
```python
from openai import OpenAI
client = OpenAI(api_key="...")

response = client.audio.speech.create(
    model="tts-1",  # Або "tts-1-hd" для якості
    voice="alloy",  # nova, shimmer, echo, onyx, fable
    input=text
)
response.stream_to_file("output.mp3")
```

**Швидкість:** 1-2 секунди
**Голоси:** 6 варіантів (жіночі/чоловічі)
**Якість:** Відмінна, природна

### Варіант Б: ElevenLabs (НАЙКРАЩА ЯКІСТЬ)
```python
import requests

response = requests.post(
    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
    headers={"xi-api-key": "your-key"},
    json={"text": text, "model_id": "eleven_multilingual_v2"}
)
```

**Голоси:** Сотні варіантів, включно з українською
**Якість:** Найкраща на ринку
**Безкоштовно:** 10,000 символів/місяць

### Варіант В: Coqui TTS (ЛОКАЛЬНИЙ)
```bash
pip install TTS
```

```python
from TTS.api import TTS

tts = TTS(model_name="tts_models/uk/mai/glow-tts")
tts.tts_to_file(text="Привіт", file_path="output.wav")
```

**Швидкість:** 0.5-1 секунда
**Якість:** Середня
**Переваги:** Офлайн, безкоштовно

### Варіант Г: Google Cloud TTS (БАГАТО ГОЛОСІВ)
```python
from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()
voice = texttospeech.VoiceSelectionParams(
    language_code="uk-UA",
    name="uk-UA-Wavenet-A"  # Жіночий голос
)
audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
)
```

**Голоси українською:** 4 варіанти (2 жіночі, 2 чоловічі)
**Якість:** Відмінна
**Безкоштовно:** 4 млн символів/місяць

---

## 4. Порівняння швидкості

| Компонент | Поточний | Швидкий варіант | Прискорення |
|-----------|----------|-----------------|-------------|
| STT | OpenAI Whisper API (3-6s) | faster-whisper (1-3s) | **2x** |
| LLM | OpenAI GPT-3.5 (3-8s) | Groq llama3 (0.5-1.5s) | **5x** |
| TTS | ? | OpenAI TTS (1-2s) | - |
| **ВСЬОГО** | **6-14s** | **2.5-6.5s** | **~3x швидше!** |

---

## 5. Рекомендації для RPi 5

### Оптимальна конфігурація:

```python
# 1. STT: faster-whisper (локально)
# 2. LLM: Groq API (швидко + якісно)
# 3. TTS: OpenAI TTS або ElevenLabs

# Очікувана швидкість: 3-5 секунд загалом
```

### Ультра-швидка конфігурація (офлайн):

```python
# 1. STT: Vosk (0.5-1s)
# 2. LLM: Ollama phi3:mini (0.5-2s)
# 3. TTS: Coqui TTS (0.5-1s)

# Очікувана швидкість: 1.5-4 секунди загалом
# Працює БЕЗ інтернету!
```

---

## Що встановити ЗАРАЗ?

**Рекомендую почати з Groq:**

1. Зареєструватись: https://console.groq.com/
2. Отримати API ключ
3. Змінити `base_url` в OpenAI клієнті

**Це дасть 5x прискорення БЕЗ зміни коду!** ⚡

