# main.py
import os
import random
import httpx
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

# --- CORS: домены фронтенда через переменную окружения ALLOW_ORIGINS ---
ALLOW_ORIGINS = [o.strip() for o in os.getenv("ALLOW_ORIGINS", "").split(",") if o.strip()]

app = FastAPI(title="Cat Facts API")

if ALLOW_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOW_ORIGINS,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

CATFACT_URL = "https://catfact.ninja/fact"
GT_URL = "https://translate.googleapis.com/translate_a/single"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# Только кошачьи категории
CAT_CATEGORIES = [
    "Category:Felis catus",
    "Category:Kittens",
    "Category:Cats",
]

# Вежливый User-Agent для Wikimedia (по их правилам)
WM_HEADERS = {
    "User-Agent": "CatFactsDemo/1.0 (contact: example@example.com)"
}

async def translate_lazy(client: httpx.AsyncClient, text: str, tl: str) -> str:
    try:
        r = await client.get(
            GT_URL,
            params={"client": "gtx", "sl": "en", "tl": tl, "dt": "t", "q": text},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            return "".join(seg[0] for seg in data[0] if seg and seg[0])
    except Exception:
        pass
    return text

@app.get("/healthz")
def health():
    return {"status": "ok"}

@app.get("/fact")
async def get_fact(lang: str = "en"):
    async with httpx.AsyncClient() as c:
        try:
            fact = (await c.get(CATFACT_URL, timeout=5)).json()["fact"]
        except Exception:
            fact = "Cats sleep 12–16 hours a day."
        if lang.lower().startswith("ru"):
            fact = await translate_lazy(c, fact, "ru")
    return {"fact": fact}

@app.get("/catimg")
async def catimg():
    """
    Проксируем случайную картинку КОТА с Wikimedia Commons:
    - корректный User-Agent
    - выбор из кошачьих категорий
    - no-cache заголовки
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=12, headers=WM_HEADERS) as c:
        try:
            # Несколько попыток: перебираем категории в случайном порядке
            for category in random.sample(CAT_CATEGORIES, k=len(CAT_CATEGORIES)):
                r = await c.get(
                    COMMONS_API,
                    params={
                        "action": "query",
                        "generator": "categorymembers",
                        "gcmtitle": category,
                        "gcmtype": "file",
                        "gcmlimit": "100",
                        "prop": "imageinfo",
                        "iiprop": "url|mime",
                        "iiurlwidth": "1200",
                        "format": "json",
                    },
                )
                pages = (r.json().get("query") or {}).get("pages") or {}
                items = [p for p in pages.values() if p.get("imageinfo")]
                if not items:
                    continue

                # Выбираем случайный файл и тянем байты
                chosen = random.choice(items)
                ii = chosen["imageinfo"][0]
                img_url = ii.get("thumburl") or ii.get("url")
                if not img_url:
                    continue

                img = await c.get(img_url)
                if img.status_code != 200 or not img.content:
                    continue

                media_type = img.headers.get("content-type", ii.get("mime") or "image/jpeg")
                return Response(
                    content=img.content,
                    media_type=media_type,
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    },
                )

            # если все категории не дали валидный ответ — фолбэк
            fb = await c.get("https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg")
            return Response(
                content=fb.content,
                media_type=fb.headers.get("content-type", "image/jpeg"),
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                },
            )
        except Exception:
            # на крайний случай — тот же фолбэк (если, например, временно нет исходящего интернета)
            try:
                fb = await c.get("https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg")
                return Response(
                    content=fb.content,
                    media_type=fb.headers.get("content-type", "image/jpeg"),
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                    },
                )
            except Exception:
                # вернём пустой 204, чтобы фронт мог показать заглушку
                return Response(status_code=204)

@app.get("/", response_class=HTMLResponse)
def ui():
    return """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Cat Facts</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:2rem;line-height:1.5}
    .box{max-width:640px;margin:auto;padding:1rem;border:1px solid #ddd;border-radius:12px}
    button,select{font-size:1rem;padding:.5rem .8rem;border-radius:.6rem;border:1px solid #ccc;cursor:pointer}
    #fact{margin-top:1rem;font-size:1.1rem}
    img{display:block;max-width:100%;height:auto;border-radius:12px;margin:.5rem 0 1rem}
  </style>
</head>
<body>
  <div class="box">
    <h1>Cat Facts 😺</h1>
    <img src="" alt="cat" id="catimg">
    <div>
      Язык:
      <select id="lang">
        <option value="en">English</option>
        <option value="ru" selected>Русский</option>
      </select>
      <button id="btn">Получить факт</button>
    </div>
    <div id="fact">Нажми кнопку, чтобы узнать факт о котах.</div>
  </div>

  <script>
    const btn = document.getElementById('btn');
    const factBox = document.getElementById('fact');
    const langSel = document.getElementById('lang');
    const img = document.getElementById('catimg');

    function newCat() { img.src = "/catimg?ts=" + Date.now(); } // анти-кэш
    newCat();

    async function loadFact() {
      factBox.textContent = 'Загрузка...';
      newCat();
      try {
        const lang = langSel.value;
        const res = await fetch('/fact?lang=' + encodeURIComponent(lang));
        const data = await res.json();
        factBox.textContent = data.fact || 'Не удалось получить факт.';
      } catch (e) {
        factBox.textContent = 'Ошибка сети.';
      }
    }
    btn.addEventListener('click', loadFact);
  </script>
</body>
</html>
"""
