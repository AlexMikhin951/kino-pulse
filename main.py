from fastapi import FastAPI, Request, Form, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import psycopg2
from psycopg2.extras import RealDictCursor
import requests
import logging
import json
from passlib.context import CryptContext

from config import DB_CONFIG, KP_KEY, OMDB_KEY, TMDB_KEY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_db_conn(): return psycopg2.connect(**DB_CONFIG, client_encoding='utf8')

def get_current_user(request: Request):
    user_id = request.cookies.get("user_id")
    if user_id:
        conn = get_db_conn()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        conn.close()
        return user
    return None

@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(password) > 50: return {"error": "Пароль не должен превышать 50 символов."}
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cur.fetchone(): return {"error": "Это имя пользователя уже занято. Попробуйте другое."}
        cur.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id", (username, pwd_context.hash(password)))
        user_id = cur.fetchone()[0]
        conn.commit()
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(key="user_id", value=str(user_id))
        return resp
    except Exception as e:
        conn.rollback()
        logger.error(f"Ошибка регистрации: {e}")
        return {"error": f"Ошибка сервера: {str(e)}"}
    finally: conn.close()

@app.post("/login")
async def login(response: Response, username: str = Form(...), password: str = Form(...)):
    if len(password) > 50: return {"error": "Неверный логин или пароль."}
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cur.fetchone()
    conn.close()
    if not user: return {"error": f"Пользователь с именем '{username}' не найден. Проверьте логин."}
    if pwd_context.verify(password, user['password_hash']):
        resp = RedirectResponse(url="/", status_code=303)
        resp.set_cookie(key="user_id", value=str(user['id']))
        return resp
    else: return {"error": "Неверный пароль. Попробуйте еще раз."}

@app.get("/logout")
async def logout():
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie("user_id")
    return resp

# ИСПРАВЛЕНИЕ ЗДЕСЬ: min_rating теперь принимает строку (str), чтобы не падать от пустого поля
@app.get("/")
async def index(request: Request, search: str = None, genre: str = None, year: str = None, 
                actor: str = None, director: str = None, tag: str = None, min_rating: str = None, 
                sort: str = "popular", offset: int = 0):
    user = get_current_user(request)
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    limit = 24
    
    sql = "SELECT * FROM movies WHERE num_votes > 10"
    params = []
    
    if search:
        sql += " AND title ILIKE %s"
        params.append(f'%{search}%')
        
    if genre:
        sql += " AND genres ILIKE %s"
        params.append(f'%{genre}%')
        
    if year:
        if year == "2020s": sql += " AND release_year BETWEEN 2020 AND 2029"
        elif year == "2010s": sql += " AND release_year BETWEEN 2010 AND 2019"
        elif year == "2000s": sql += " AND release_year BETWEEN 2000 AND 2009"
        elif year == "1990s": sql += " AND release_year BETWEEN 1990 AND 1999"
        elif year == "old": sql += " AND release_year < 1990"

    if actor:
        actor_found = False
        try:
            person_res = requests.get(f"https://api.themoviedb.org/3/search/person?api_key={TMDB_KEY}&query={actor}", timeout=5).json()
            if person_res.get('results'):
                person_id = person_res['results'][0]['id']
                cred_res = requests.get(f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_KEY}", timeout=5).json()
                tmdb_ids = [int(m['id']) for m in cred_res.get('cast', [])]
                if tmdb_ids:
                    tmdb_ids = tmdb_ids[:300]
                    format_strings = ','.join(['%s'] * len(tmdb_ids))
                    sql += f" AND tmdb_id IN ({format_strings})"
                    params.extend(tmdb_ids)
                    actor_found = True
        except Exception as e: logger.error(f"Ошибка поиска актера: {e}")
        if not actor_found: sql += " AND FALSE"

    if director:
        director_found = False
        try:
            person_res = requests.get(f"https://api.themoviedb.org/3/search/person?api_key={TMDB_KEY}&query={director}", timeout=5).json()
            if person_res.get('results'):
                person_id = person_res['results'][0]['id']
                cred_res = requests.get(f"https://api.themoviedb.org/3/person/{person_id}/movie_credits?api_key={TMDB_KEY}", timeout=5).json()
                tmdb_ids = [int(m['id']) for m in cred_res.get('crew', []) if m.get('job') == 'Director']
                if tmdb_ids:
                    tmdb_ids = tmdb_ids[:300]
                    format_strings = ','.join(['%s'] * len(tmdb_ids))
                    sql += f" AND tmdb_id IN ({format_strings})"
                    params.extend(tmdb_ids)
                    director_found = True
        except Exception as e: logger.error(f"Ошибка поиска режиссера: {e}")
        if not director_found: sql += " AND FALSE"

    if tag:
        sql += " AND movie_id IN (SELECT movie_id FROM movie_tags WHERE tag ILIKE %s)"
        params.append(f"%{tag}%")

    # ИСПРАВЛЕНИЕ: Безопасное превращение строки рейтинга в число
    min_rating_val = None
    if min_rating and min_rating.strip() != "":
        try:
            min_rating_val = float(min_rating)
            sql += " AND rating_avg >= %s"
            params.append(min_rating_val / 2)
        except ValueError:
            pass

    if sort == "new": sql += " ORDER BY release_year DESC NULLS LAST, num_votes DESC"
    elif sort == "rating": sql += " ORDER BY rating_avg DESC, num_votes DESC"
    else: sql += " ORDER BY num_votes DESC NULLS LAST, rating_avg DESC"
    
    cur.execute(sql + " LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
    movies = cur.fetchall()
    
    for m in movies:
        if not m.get('poster_url'): m['poster_url'] = f"https://placehold.co/250x380/1a1a2e/8a2be2?text={m['title'][:15]}"
        
    cur.close()
    conn.close()
    
    if offset > 0: return templates.TemplateResponse(request=request, name="movie_list_part.html", context={"movies": movies})
    return templates.TemplateResponse(request=request, name="index.html", 
        context={"movies": movies, "search": search, "genre": genre, "year": year, 
                 "actor": actor, "director": director, "tag": tag, "min_rating": min_rating_val, 
                 "sort": sort, "user": user})

@app.get("/movie/{movie_id}")
async def movie_detail(request: Request, movie_id: int):
    user = get_current_user(request)
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM movies WHERE movie_id = %s", (movie_id,))
    movie = cur.fetchone()
    
    cur.execute("SELECT movie_id, title, poster_url FROM movies WHERE genres = %s AND movie_id != %s AND poster_url IS NOT NULL ORDER BY num_votes DESC LIMIT 6", (movie['genres'], movie_id))
    similar = cur.fetchall()
    
    cur.execute("SELECT tag, tag_count FROM movie_tags WHERE movie_id = %s ORDER BY tag_count DESC LIMIT 15", (movie_id,))
    tags = cur.fetchall()
    
    cur.execute("SELECT c.text, c.rating, c.created_at, u.username FROM comments c JOIN users u ON c.user_id = u.id WHERE c.movie_id = %s ORDER BY c.created_at DESC", (movie_id,))
    comments = cur.fetchall()
    
    cur.execute("SELECT AVG(rating)::numeric(10,1) as local_rating, COUNT(rating) as local_votes FROM comments WHERE movie_id = %s AND rating IS NOT NULL", (movie_id,))
    local_stats = cur.fetchone()
    
    cur.close()
    conn.close()

    comparison_text = None
    if local_stats and local_stats['local_rating'] and movie.get('rating_avg'):
        local_r = float(local_stats['local_rating'])
        global_r = float(movie['rating_avg']) * 2 
        
        diff = ((local_r - global_r) / global_r) * 100
        if diff > 5:
            comparison_text = f"📈 Рейтинг этого фильма на нашем сайте ({local_r}) на {abs(diff):.1f}% ВЫШЕ, чем в среднем по миру."
        elif diff < -5:
            comparison_text = f"📉 Пользователи нашего сайта оценивают этот фильм на {abs(diff):.1f}% НИЖЕ ({local_r}), чем мировые агрегаторы."
        else:
            comparison_text = f"📊 Оценки наших пользователей ({local_r}) почти совпадают с мировым рейтингом."

    return templates.TemplateResponse(request=request, name="movie.html", context={"movie": movie, "similar": similar, "tags": tags, "comments": comments, "user": user, "comparison_text": comparison_text, "local_stats": local_stats})

@app.post("/api/comments")
async def add_comment(request: Request):
    user = get_current_user(request)
    if not user: return {"status": "error", "msg": "Нужно войти"}
    data = await request.json()
    conn = get_db_conn()
    cur = conn.cursor()
    
    rating = data.get('rating')
    if rating: rating = int(rating)
    
    cur.execute("INSERT INTO comments (movie_id, user_id, text, rating) VALUES (%s, %s, %s, %s)", (data['movie_id'], user['id'], data['text'], rating))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/parse/{imdb_id}")
def parse_movie_data(imdb_id: str, title: str, year: int = None):
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT data FROM movie_cache WHERE imdb_id = %s", (imdb_id,))
    cached = cur.fetchone()
    
    if cached:
        parsed_data = cached['data']
        return parsed_data

    data = { 
        "plot": "Описание не найдено.", "poster": None, "box_office": "N/A", 
        "director": "N/A", "runtime": "N/A", "country": "N/A",
        "actors": "N/A", "awards": "Нет информации", "budget": 0, "revenue": 0,
        "box_office_details": {"rus": 0, "usa": 0, "world": 0},
        "ratings": {"kp": None, "tmdb": None, "rt": None, "mc": None}, 
        "trailer_url": None, 
        "links": [], "reviews":[]
    }

    try:
        r = requests.get(f"https://api.themoviedb.org/3/find/{imdb_id}?api_key={TMDB_KEY}&external_source=imdb_id", timeout=5).json()
        if r.get('movie_results'):
            res = r['movie_results'][0]
            tmdb_id_internal = res.get('id')
            data['ratings']['tmdb'] = str(round(res.get('vote_average', 0), 1))
            data['plot'] = res.get('overview')
            if res.get('poster_path'): data['poster'] = f"https://image.tmdb.org/t/p/w500{res['poster_path']}"
            
            det_r = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id_internal}?api_key={TMDB_KEY}&append_to_response=videos", timeout=5).json()
            data['budget'] = det_r.get('budget', 0)
            data['revenue'] = det_r.get('revenue', 0)
            
            if 'videos' in det_r and 'results' in det_r['videos']:
                for vid in det_r['videos']['results']:
                    if vid.get('site') == 'YouTube' and vid.get('type') == 'Trailer':
                        data['trailer_url'] = f"https://www.youtube.com/embed/{vid.get('key')}?autoplay=0&rel=0"
                        break

            rev_r = requests.get(f"https://api.themoviedb.org/3/movie/{tmdb_id_internal}/reviews?api_key={TMDB_KEY}", timeout=5).json()
            for rev in rev_r.get('results', [])[:15]:
                data['reviews'].append({
                    "source": "TMDB", "author": rev['author'], 
                    "text": rev['content'][:500] + "...", "type": "NEUTRAL",
                    "author_rating": rev.get('author_details', {}).get('rating')
                })
    except: pass

    try:
        r = requests.get(f"https://www.omdbapi.com/?i={imdb_id}&apikey={OMDB_KEY}", timeout=5).json()
        if r.get('Response') == 'True':
            data['box_office'] = r.get('BoxOffice', 'N/A')
            data['director'] = r.get('Director', 'N/A')
            data['runtime'] = r.get('Runtime', 'N/A')
            data['country'] = r.get('Country', 'N/A')
            data['actors'] = r.get('Actors', 'N/A')
            data['awards'] = r.get('Awards', 'Нет информации')
            for rat in r.get('Ratings', []):
                if rat['Source'] == 'Rotten Tomatoes': data['ratings']['rt'] = rat['Value']
                if rat['Source'] == 'Metacritic': data['ratings']['mc'] = rat['Value']
    except: pass

    try:
        headers = {"X-API-KEY": KP_KEY, "Content-Type": "application/json"}
        search_query = f"{title} {year}" if year else title
        kp_s = requests.get(f"https://kinopoiskapiunofficial.tech/api/v2.1/films/search-by-keyword?keyword={search_query}", headers=headers, timeout=5).json()
        if kp_s.get('films'):
            kid = kp_s['films'][0]['filmId']
            det = requests.get(f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{kid}", headers=headers).json()
            data['ratings']['kp'] = str(det.get('ratingKinopoisk') or "N/A")
            
            if not data['trailer_url']:
                try:
                    vid_req = requests.get(f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{kid}/videos", headers=headers, timeout=5).json()
                    for v in vid_req.get('items', []):
                        url = v.get('url', '')
                        if 'youtube.com/watch?v=' in url:
                            data['trailer_url'] = url.replace('watch?v=', 'embed/')
                            break
                        elif 'youtu.be/' in url:
                            data['trailer_url'] = url.replace('youtu.be/', 'www.youtube.com/embed/')
                            break
                except: pass

            try:
                box_req = requests.get(f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{kid}/box_office", headers=headers, timeout=5).json()
                for item in box_req.get('items', []):
                    if item['type'] == 'RUS': data['box_office_details']['rus'] = item['amount']
                    if item['type'] == 'USA': data['box_office_details']['usa'] = item['amount']
                    if item['type'] == 'WORLD': data['box_office_details']['world'] = item['amount']
            except: pass

            revs = requests.get(f"https://kinopoiskapiunofficial.tech/api/v2.2/films/{kid}/reviews", headers=headers).json()
            for r in revs.get('items', [])[:15]:
                data['reviews'].append({"source": "Кинопоиск", "author": r['author'], "text": r['description'][:500] + "...", "type": r['type']})
    except: pass

    try:
        cur.execute("INSERT INTO movie_cache (imdb_id, data) VALUES (%s, %s) ON CONFLICT (imdb_id) DO UPDATE SET data = EXCLUDED.data", (imdb_id, json.dumps(data)))
        conn.commit()
    except: pass
    finally: conn.close()
    
    return data