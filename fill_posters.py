import psycopg2
import requests
from psycopg2.extras import RealDictCursor, execute_batch
from concurrent.futures import ThreadPoolExecutor
import time

from config import DB_CONFIG, TMDB_KEY
THREADS = 20  # Количество одновременных потоков (не ставь больше 40)

def get_poster_from_api(movie):
    """Функция для одного запроса (будет запущена в потоках)"""
    try:
        url = f"https://api.themoviedb.org/3/movie/{movie['tmdb_id']}?api_key={TMDB_KEY}"
        r = requests.get(url, timeout=5).json()
        if r.get('poster_path'):
            return (f"https://image.tmdb.org/t/p/w300{r['poster_path']}", movie['movie_id'])
        return ('none', movie['movie_id'])
    except:
        return None

def turbo_fill():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    # Берем ВСЕ фильмы без постеров
    cur.execute("SELECT movie_id, tmdb_id FROM movies WHERE poster_url IS NULL AND tmdb_id IS NOT NULL ORDER BY num_votes DESC")
    movies = cur.fetchall()
    total = len(movies)
    print(f"🚀 Начинаю турбо-загрузку {total} постеров в {THREADS} потоков...")

    results = []
    # Используем пул потоков для параллельных запросов
    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i, res in enumerate(executor.map(get_poster_from_api, movies)):
            if res:
                results.append(res)
            
            # Каждые 500 найденных ссылок записываем в базу пачкой (это быстрее)
            if len(results) >= 500:
                cur_write = conn.cursor()
                execute_batch(cur_write, "UPDATE movies SET poster_url = %s WHERE movie_id = %s", results)
                conn.commit()
                results = []
                print(f"📊 Прогресс: {i+1}/{total} обработано...")

    # Дозаписываем остатки
    if results:
        cur_write = conn.cursor()
        execute_batch(cur_write, "UPDATE movies SET poster_url = %s WHERE movie_id = %s", results)
        conn.commit()

    cur.close()
    conn.close()
    print("✅ ВСЕ ПОСТЕРЫ ЗАГРУЖЕНЫ!")

if __name__ == "__main__":
    turbo_fill()