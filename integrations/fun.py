"""
Інтеграція з API для жартів та цікавих фактів
"""

from typing import Tuple
import requests
import random


class FunManager:
    """Менеджер жартів та цікавих фактів"""

    def __init__(self):
        self.joke_api = "https://official-joke-api.appspot.com/random_joke"
        self.fact_api = "https://uselessfacts.jsph.pl/random.json?language=en"
        
        # Українські жарти (fallback якщо API не працює)
        # Британський стиль: самоіронія, абсурд, understatement
        self.ukrainian_jokes = [
            "Мій дідусь прожив 103 роки. Секрет довголіття? Він ніколи не сперечався з бабусею. Навіть коли вона була неправа. Особливо коли вона була неправа.",
            "Я не кажу, що мій кіт мене ігнорує, але коли я прийшов додому після відпустки, він подивився на мене і зітхнув так, ніби я зіпсував йому день.",
            "Пішов до лікаря. Він каже: 'Вам треба більше відпочивати.' Я кажу: 'Добре.' Він: 'І менше хвилюватись.' Я: 'А як?' Він: 'Це не моя проблема, я ж лікар, а не чарівник.'",
            "Моя проблема в тому, що між 'Зараз це зроблю' і 'Вже зробив' у мене є стадія 'Хм, може чаю випити?', яка якимось чином займає 4 години.",
            "Запитують у письменника: 'Як ви пишете такі захопливі детективи?' - 'Та я просто описую, як намагаюсь знайти пульт від телевізора.'",
            "Я б організував своє життя, але кожен раз, коли починаю, мені терміново потрібно перевірити, чи справді пінгвіни мають коліна. Мають, до речі.",
            "Мій рівень мотивації сьогодні можна описати як 'Хотів би я хотіти щось робити'.",
            "Я не ліниюсь. Я просто в режимі енергозбереження. Постійно.",
        ]
        
        self.ukrainian_facts = [
            "💡 Найдовша книга у світі — 'У пошуках втраченого часу' Марселя Пруста. 9 609 000 слів. Ідеально для безсоння!",
            "💡 Осьминоги мають три серця і сині кров. Два серця качають кров через зябра, третє — по всьому тілу.",
            "💡 Ейфелева вежа влітку вища на 15 см через розширення металу від спеки. Фізика, знаєте.",
            "💡 Щастя має запах. Науковці виявили, що щасливі люди виділяють особливі феромони, які можуть покращити настрій оточуючим.",
            "💡 У просторі панує повна тиша. Звукові хвилі потребують середовища для поширення, а у вакуумі його немає.",
            "💡 Бібліотека Конгресу США зберігає 38 мільйонів книг. Якби ви читали одну книгу на день, вам знадобилося б 104 000 років.",
            "💡 Мед — єдина їжа, яка ніколи не псується. Археологи знаходили горщики з медом у гробницях фараонів, і він був цілком придатний до вживання.",
            "💡 Фінляндія — найщасливіша країна світу за рейтингом ООН. Можливо, секрет у сауні та спокої?",
        ]

    def get_joke(self, language: str = "uk") -> Tuple[bool, str]:
        """
        Отримує випадковий жарт
        
        Args:
            language: uk, en, de
        """
        if language == "uk":
            joke = random.choice(self.ukrainian_jokes)
            return True, f"😄 {joke}"
        
        try:
            response = requests.get(self.joke_api, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            setup = data.get('setup', '')
            punchline = data.get('punchline', '')
            
            return True, f"😄 {setup}\n\n...{punchline}"
                
        except Exception as e:
            print(f"⚠️ Joke API error: {e}")
            if language == "uk":
                joke = random.choice(self.ukrainian_jokes)
                return True, f"😄 {joke}"
            elif language == "de":
                return False, "❌ Fehler beim Abrufen des Witzes"
            else:
                return False, "❌ Error fetching joke"

    def get_fact(self, language: str = "uk") -> Tuple[bool, str]:
        """
        Отримує випадковий цікавий факт
        
        Args:
            language: uk, en, de
        """
        if language == "uk":
            fact = random.choice(self.ukrainian_facts)
            return True, fact
        
        try:
            response = requests.get(self.fact_api, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            fact_text = data.get('text', '')
            
            if not fact_text:
                raise ValueError("Empty fact")
            
            if language == "de":
                prefix = "💡"
            else:  # en
                prefix = "💡"
            
            return True, f"{prefix} {fact_text}"
                
        except Exception as e:
            print(f"⚠️ Fact API error: {e}")
            if language == "uk":
                fact = random.choice(self.ukrainian_facts)
                return True, fact
            elif language == "de":
                return False, "❌ Fehler beim Abrufen der Fakten"
            else:
                return False, "❌ Error fetching fact"

    def get_random_fun(self, language: str = "uk") -> Tuple[bool, str]:
        """Випадково обирає жарт або факт"""
        if random.choice([True, False]):
            return self.get_joke(language)
        else:
            return self.get_fact(language)


# Глобальний екземпляр
fun_manager = FunManager()