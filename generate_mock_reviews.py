import psycopg2
import random
from psycopg2.extras import execute_batch
from passlib.context import CryptContext

from config import DB_CONFIG

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# === ОБЩИЕ ПУЛЫ ДЛЯ ГЕНЕРАЦИИ (40x40x40 = 64 000 комбинаций) ===
LAST_NAMES = [
    "Иванов", "Смирнов", "Smith", "Garcia", "Wang", "Kim", "Silva", "Rossi", 
    "Muller", "Ali", "Gonzalez", "Lee", "Martin", "Sato", "Suzuki", "Davis", 
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Perez", "Williams", "Brown", 
    "Taylor", "Moore", "Anderson", "Thomas", "Jackson", "White", "Harris", 
    "Clark", "Lewis", "Robinson", "Walker", "Hall", "Allen", "Young", "King", 
    "Wright", "Scott"
]

FIRST_NAMES = [
    "Александр", "Мария", "John", "Akio", "Fatima", "Diego", "Chen", "Светлана", 
    "Hans", "Chloe", "Ahmed", "Olga", "Liam", "Sakura", "Boris", "Emma", 
    "Youssef", "Anna", "Luigi", "Isabella", "Wei", "Mateo", "Sophia", "Hiroshi", 
    "Mia", "Santiago", "Yuki", "Lucas", "Amelia", "Omar", "Elena", "Noah", 
    "Aria", "Taro", "Zoe", "Hassan", "Charlotte", "Jack", "Harper", "Ali"
]

MIDDLE_NAMES = [
    "Александрович", "James", "Marie", "Петровна", "Wei", "Antonio", "Lee", "Дмитриевич", 
    "Rose", "Eduardo", "Kenji", "Ивановна", "Grace", "Luis", "Akemi", "Сергеевич", 
    "Elizabeth", "Carlos", "Yuki", "Николаевич", "Ann", "Jose", "Mei", "Владимирович", 
    "Lynn", "Jorge", "Haruki", "Андреевна", "Jane", "Pedro", "Sakura", "Павлович", 
    "Mae", "Juan", "Aiko", "Михайловна", "Claire", "Miguel", "Naomi", "Романович"
]

# === ПУЛЫ ОТЗЫВОВ ===
POSITIVE_REVIEWS = [
    "Отличный фильм! Смотрел на одном дыхании.", "Шедевр кинематографа, 10 из 10.", 
    "Очень крутая актерская игра.", "Один из лучших фильмов, что я видел за последнее время.", 
    "Прекрасная работа режиссера. Буду пересматривать.", "Оставил после себя долгое послевкусие, советую всем.", 
    "Просто супер, сюжет держит в напряжении до самого конца.", "Я в восторге! Графика, звук, сюжет - все на высоте.",
    "Браво создателям!", "Невероятные эмоции после просмотра.", "Обязательно посмотрите, это нечто.",
    "Фильм, который заставляет задуматься.", "Потрясающая атмосфера и саундтрек.", "Давно я так не сопереживал героям.",
    "Эталон жанра.", "Мой новый любимый фильм.", "Рекомендую к просмотру на большом экране!"
]
NEUTRAL_REVIEWS = [
    "Нормальный фильм, на один раз пойдет.", "Местами затянуто, но в целом смотреть можно.", 
    "Идея хорошая, но реализация подкачала.", "Середнячок, ничего особенного.", 
    "Ожидал большего, но вечер убить сойдет.", "Актеры старались, но сценарий слабый.", 
    "Смотрибельно, но через неделю забуду о чем он.", "50/50, есть плюсы и минусы.",
    "Картинка красивая, но смысл теряется.", "Можно фоном включить.", "Неплохо, но пересматривать точно не стану.",
    "Начало бодрое, а конец слили.", "Ни рыба ни мясо.", "Для поклонников жанра пойдет."
]
NEGATIVE_REVIEWS = [
    "Ужасно. Зря потраченное время.", "Полный бред, сюжет нелогичный.", 
    "Худшее, что я видел в этом году.", "Не советую, игра актеров просто картонная.", 
    "Заснул на середине, невероятно скучно.", "Как на это вообще дали деньги? Кошмар.", 
    "Разочарование года.", "Сценарий писала нейросеть?", "Глупые диалоги, отсутствие логики.",
    "Еле досмотрел до конца.", "Даже одна звезда - это слишком много для этого.", "Кровь из глаз от таких спецэффектов.",
    "Жаль потраченных денег на билет.", "Никакой актерской игры вообще.", "Какая-то бессмыслица."
]

SUFFIXES = ["", "!", ".", "...", " 100%", " Рекомендую!", " Ну такое.", " 🤦‍♂️", " 🔥", " 👍", " 👎"]

def generate_username():
    """Случайная комбинация Фамилия_Имя_Отчество из пулов"""
    return f"{random.choice(LAST_NAMES)}_{random.choice(FIRST_NAMES)}_{random.choice(MIDDLE_NAMES)}"

def turbo_generate():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("🚀 1. Подготовка пользователей...")
    # Хешируем пароль один раз для экономии времени
    common_password_hash = pwd_context.hash("123456789")
    
    # Генерируем 5000 уникальных никнеймов
    unique_usernames = set()
    while len(unique_usernames) < 5000:
        unique_usernames.add(generate_username())

    users_data = [(uname, common_password_hash) for uname in unique_usernames]

    print("🚀 2. Загрузка 5000 пользователей в базу (пароль у всех: 123456789)...")
    execute_batch(cur, """
        INSERT INTO users (username, password_hash) 
        VALUES (%s, %s) 
        ON CONFLICT (username) DO NOTHING
    """, users_data)
    conn.commit()

    cur.execute("SELECT id FROM users")
    user_ids = [row[0] for row in cur.fetchall()]
    if not user_ids:
        print("❌ Ошибка: нет пользователей в базе.")
        return

    print("🚀 3. Получаем ТОП-1000 фильмов...")
    cur.execute("SELECT movie_id FROM movies ORDER BY num_votes DESC LIMIT 1000")
    movies = [row[0] for row in cur.fetchall()]

    print("🚀 4. Массовая генерация 50 000 отзывов...")
    reviews_data = []
    
    for movie_id in movies:
        # Для каждого из 1000 фильмов генерируем от 35 до 65 отзывов (в среднем 50)
        num_reviews = random.randint(35, 65)
        
        # Выбираем случайных УНИКАЛЬНЫХ пользователей для этого фильма
        reviewers = random.sample(user_ids, num_reviews)
        
        for user_id in reviewers:
            rating = random.choices(
                [1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 
                weights=[2, 2, 3, 4, 10, 15, 20, 20, 15, 9]
            )[0]
            
            if rating >= 8: base_text = random.choice(POSITIVE_REVIEWS)
            elif rating >= 5: base_text = random.choice(NEUTRAL_REVIEWS)
            else: base_text = random.choice(NEGATIVE_REVIEWS)
                
            final_text = base_text + random.choice(SUFFIXES)

            reviews_data.append((movie_id, user_id, final_text, rating))

    print(f"📊 Сгенерировано {len(reviews_data)} отзывов в памяти. Начинаю запись в БД...")

    # Вставляем пачками по 5000 строк
    batch_size = 5000
    for i in range(0, len(reviews_data), batch_size):
        batch = reviews_data[i:i+batch_size]
        execute_batch(cur, """
            INSERT INTO comments (movie_id, user_id, text, rating) 
            VALUES (%s, %s, %s, %s)
        """, batch)
        conn.commit()
        print(f"   Записано {min(i+batch_size, len(reviews_data))} / {len(reviews_data)}...")

    cur.close()
    conn.close()
    print("✅ ГОТОВО! Массив данных успешно загружен.")

if __name__ == "__main__":
    turbo_generate()