import psycopg2

from config import DB_CONFIG

def clear():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE movie_cache;") # Эта команда удаляет всё из таблицы кэша
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Кэш фильмов успешно очищен! Теперь скрипт заново найдет все трейлеры.")

if __name__ == "__main__":
    clear()