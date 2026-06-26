# 🎬 КИНО ПУЛЬС

> **Краткое описание для GitHub:** Fullstack-платформа аналитики фильмов на FastAPI + PostgreSQL с датасетом MovieLens 32M, фильтрацией, авторизацией и агрегацией данных из TMDB, OMDB и Кинопоиска.

Веб-приложение для поиска, фильтрации и анализа фильмов на основе **32 миллионов пользовательских оценок** (MovieLens 32M). Проект объединяет работу с реляционной БД, ETL-пайплайн, внешние API и полноценный UI с авторизацией и отзывами.

<div align="center">
  <img width="1568" height="1000" alt="image" src="https://github.com/user-attachments/assets/0d2bacd6-eba4-4263-9a7a-048bbf83b9ec" />
  <img width="1253" height="206" alt="image" src="https://github.com/user-attachments/assets/b521c5e0-d2fe-47c6-be8a-1bb903d7ca31" />
  <img width="1263" height="686" alt="image" src="https://github.com/user-attachments/assets/3973142b-9e52-489d-a966-0497214ca9e3" />
  <img width="1256" height="684" alt="image" src="https://github.com/user-attachments/assets/cec4c34a-0f4f-40c5-9ec9-afa0bff35b6a" />
  <img width="1147" height="842" alt="image" src="https://github.com/user-attachments/assets/c371fe1b-1cb1-48ee-bcb7-ef24e8ff4955" />
</div>

---

## ✨ Возможности

- **Каталог фильмов** — поиск по названию, жанру, десятилетию, минимальному рейтингу
- **Расширенные фильтры** — поиск по актёру и режиссёру через TMDB API, фильтрация по пользовательским тегам
- **Карточка фильма** — описание, постер, трейлер, сборы, рейтинги с нескольких платформ (TMDB, Rotten Tomatoes, Metacritic, Кинопоиск)
- **Сравнение рейтингов** — локальные оценки пользователей сайта vs. мировые агрегаторы
- **Авторизация** — регистрация и вход, хеширование паролей (Argon2)
- **Отзывы и оценки** — комментарии пользователей с рейтингом 1–10
- **Infinite scroll** — подгрузка каталога без перезагрузки страницы
- **Кэширование** — данные из внешних API сохраняются в PostgreSQL

---

## 🛠 Стек технологий

| Слой | Технологии |
|------|------------|
| Backend | Python 3.10+, FastAPI, Jinja2 |
| База данных | PostgreSQL, psycopg2 |
| ETL / аналитика | pandas, batch-загрузка |
| Безопасность | passlib (Argon2) |
| Frontend | Bootstrap 5, Font Awesome, vanilla JS |
| Внешние API | TMDB, OMDB, Kinopoisk Unofficial API |

---

## 🏗 Архитектура

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Browser   │────▶│   FastAPI    │────▶│   PostgreSQL    │
│  (Jinja2)   │◀────│   main.py    │◀────│  movie_analytics│
└─────────────┘     └──────┬───────┘     └─────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
          TMDB API    OMDB API    Kinopoisk API
```

**ETL-скрипты** (запускаются отдельно):

| Скрипт | Назначение |
|--------|------------|
| `load_ml_32.py` | Загрузка фильмов, агрегация 32M оценок, теги |
| `fill_posters.py` | Параллельная загрузка постеров из TMDB |
| `setup_db.py` | Создание таблиц пользователей и комментариев |
| `generate_mock_reviews.py` | Генерация тестовых отзывов |
| `clear_cache.py` | Очистка кэша внешних API |

---

## 🗄 Схема базы данных

```
movies          — каталог фильмов (title, year, genres, rating_avg, num_votes, tmdb_id, imdb_id, poster_url)
movie_tags      — пользовательские теги из MovieLens (movie_id, tag, tag_count)
users           — аккаунты (username, password_hash)
comments        — отзывы и локальные оценки (movie_id, user_id, text, rating)
movie_cache     — JSON-кэш данных из внешних API (imdb_id, data)
```

---

## 🚀 Быстрый старт

### 1. Клонировать репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/kino-pulse.git
cd kino-pulse
```

### 2. Установить зависимости

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
```

### 3. Настроить переменные окружения

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # Linux / macOS
```

Заполните `.env` — пароль PostgreSQL и API-ключи:

| Переменная | Где получить |
|------------|--------------|
| `TMDB_API_KEY` | [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api) |
| `OMDB_API_KEY` | [omdbapi.com/apikey.aspx](https://www.omdbapi.com/apikey.aspx) |
| `KINOPOISK_API_KEY` | [kinopoiskapiunofficial.tech](https://kinopoiskapiunofficial.tech/) |

### 4. Поднять PostgreSQL

```sql
CREATE DATABASE movie_analytics;
```

Создайте основные таблицы (если их ещё нет) и выполните:

```bash
python setup_db.py
```

### 5. Скачать датасет MovieLens 32M

> ⚠️ Датасет **не включён** в репозиторий (~250 MB архив, ~1 GB распакованный).

1. Скачайте с [grouplens.org/datasets/movielens/32m](https://grouplens.org/datasets/movielens/32m/)
2. Распакуйте в папку `ml-32m/` в корне проекта
3. Загрузите данные в БД (~10–15 минут):

```bash
python load_ml_32.py
```

### 6. (Опционально) Загрузить постеры

```bash
python fill_posters.py
```

### 7. Запустить приложение

```bash
uvicorn main:app --reload
```

Откройте [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## 📁 Структура проекта

```
.
├── main.py                 # FastAPI-приложение, маршруты, API
├── config.py               # Конфигурация из переменных окружения
├── setup_db.py             # Миграции таблиц users / comments
├── load_ml_32.py           # ETL: MovieLens 32M → PostgreSQL
├── fill_posters.py         # Загрузка постеров (TMDB, многопоточность)
├── generate_mock_reviews.py
├── clear_cache.py
├── templates/              # Jinja2-шаблоны
│   ├── base.html
│   ├── index.html
│   ├── movie.html
│   └── movie_list_part.html
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## 🔍 Примеры SQL-запросов

**Топ-10 фильмов по количеству оценок:**

```sql
SELECT title, release_year, rating_avg, num_votes
FROM movies
WHERE num_votes > 1000
ORDER BY num_votes DESC
LIMIT 10;
```

**Самые популярные теги для конкретного фильма:**

```sql
SELECT tag, tag_count
FROM movie_tags
WHERE movie_id = 1
ORDER BY tag_count DESC
LIMIT 10;
```

**Сравнение локального и глобального рейтинга:**

```sql
SELECT m.title,
       m.rating_avg * 2 AS global_rating,
       AVG(c.rating)    AS local_rating,
       COUNT(c.rating)  AS local_votes
FROM movies m
JOIN comments c ON c.movie_id = m.movie_id AND c.rating IS NOT NULL
GROUP BY m.movie_id, m.title, m.rating_avg
HAVING COUNT(c.rating) >= 5
ORDER BY ABS(AVG(c.rating) - m.rating_avg * 2) DESC
LIMIT 10;
```

---

## 📸 Скриншоты

> Добавьте 2–3 скриншота в папку `docs/screenshots/` и вставьте ссылки сюда перед публикацией.

<!-- ![Каталог фильмов](docs/screenshots/catalog.png) -->
<!-- ![Карточка фильма](docs/screenshots/movie-detail.png) -->

---

## ⚠️ Ограничения и заметки

- Внешние API (особенно Кинопоиск) имеют лимиты запросов — для этого используется таблица `movie_cache`
- Полная загрузка MovieLens 32M требует ~10–15 минут и достаточного места на диске
- Cookie-авторизация подходит для учебного проекта; для production стоит добавить JWT или session middleware с `httponly`/`secure` флагами
