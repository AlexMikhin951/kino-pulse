import psycopg2

from config import DB_CONFIG

def upgrade_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    print("🚀 Обновляю таблицы...")
    
    # Создаем таблицы, если их нет
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            session_token VARCHAR(255)
        );
        CREATE TABLE IF NOT EXISTS comments (
            id SERIAL PRIMARY KEY,
            movie_id INTEGER NOT NULL,
            user_id INTEGER REFERENCES users(id),
            text TEXT NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 10), -- НОВОЕ ПОЛЕ ОЦЕНКИ
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Пытаемся добавить колонку rating, если таблица comments уже существовала
    try:
        cur.execute("ALTER TABLE comments ADD COLUMN rating INTEGER CHECK (rating >= 1 AND rating <= 10);")
        print("✅ Колонка 'rating' успешно добавлена в таблицу comments.")
    except psycopg2.errors.DuplicateColumn:
        print("ℹ️ Колонка 'rating' уже существует.")
        conn.rollback()
        
    conn.commit()
    cur.close()
    conn.close()
    print("✅ База готова!")

if __name__ == "__main__":
    upgrade_db()