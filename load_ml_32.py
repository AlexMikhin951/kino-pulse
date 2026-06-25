import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch
import re

from config import DB_CONFIG, ML32M_DIR

DATA_DIR = ML32M_DIR

def load():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("🚀 1. Загрузка фильмов и ссылок (movies.csv + links.csv)...")
    movies_df = pd.read_csv(DATA_DIR / "movies.csv")
    links_df = pd.read_csv(DATA_DIR / "links.csv")
    
    # Объединяем датафреймы
    df = pd.merge(movies_df, links_df, on='movieId', how='left')

    movie_data = []
    for _, r in df.iterrows():
        # Вытаскиваем год
        year_match = re.search(r'\((\d{4})\)', r['title'])
        year = int(year_match.group(1)) if year_match else None
        title = re.sub(r'\(\d{4}\)', '', r['title']).strip()
        
        # БЕЗОПАСНАЯ ПРОВЕРКА НА NaN (чтобы не было ошибки float NaN to integer)
        imdb_id = f"tt{str(int(r['imdbId'])).zfill(7)}" if pd.notna(r['imdbId']) else None
        tmdb_id = int(r['tmdbId']) if pd.notna(r['tmdbId']) else None

        movie_data.append((int(r['movieId']), title, year, r['genres'], tmdb_id, imdb_id))

    print("Вставляем фильмы в базу...")
    # МАГИЯ ЗДЕСЬ: ON CONFLICT (movie_id) DO NOTHING защищает от ошибки дубликатов!
    query_movies = """
        INSERT INTO movies (movie_id, title, release_year, genres, tmdb_id, imdb_id) 
        VALUES (%s,%s,%s,%s,%s,%s) 
        ON CONFLICT (movie_id) DO NOTHING
    """
    execute_batch(cur, query_movies, movie_data)
    conn.commit()

    print("🚀 2. Обработка 32 000 000 оценок. Это займет около 10-15 минут...")
    chunk_size = 1000000
    count = 0
    for chunk in pd.read_csv(DATA_DIR / "ratings.csv", chunksize=chunk_size):
        # Агрегация: считаем среднее и количество голосов
        stats = chunk.groupby('movieId')['rating'].agg(['mean', 'count']).reset_index()
        
        # pd.notna страхует от пустых строк
        data = [(float(r['mean']), int(r['count']), int(r['movieId'])) for _, r in stats.iterrows() if pd.notna(r['mean'])]
        
        execute_batch(cur, """
            UPDATE movies 
            SET rating_avg = (rating_avg + %s) / 2, 
                num_votes = num_votes + %s 
            WHERE movie_id = %s
        """, data)
        conn.commit()
        count += 1
        print(f"Обработано {count} млн оценок...")

    print("🚀 3. Загрузка эмоциональных тегов (tags.csv)...")
    tags_df = pd.read_csv(DATA_DIR / "tags.csv", usecols=['movieId', 'tag']).dropna()
    
    # Берем только популярные теги (которые встретились больше 1 раза)
    tag_counts = tags_df.groupby(['movieId', 'tag']).size().reset_index(name='c')
    tag_data = [(int(r['movieId']), str(r['tag'])[:50].lower(), int(r['c'])) for _, r in tag_counts.iterrows() if r['c'] > 1]
    
    query_tags = """
        INSERT INTO movie_tags (movie_id, tag, tag_count) 
        VALUES (%s, %s, %s) 
    """
    execute_batch(cur, query_tags, tag_data)
    conn.commit()

    print("✅ ВСЁ ГОТОВО! 32 миллиона записей загружены и проанализированы.")
    cur.close()
    conn.close()

if __name__ == "__main__":
    load()