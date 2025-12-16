# main.py
import os
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

# TheCatAPI (без ключа)
CAT_API_URL = "https://api.thecatapi.com/v1/images/search"

def no_cache_headers():
    return {
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0",
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
    Проксируем случайную картинку кота через TheCatAPI (без ключа).
    """
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as c:
        try:
            # 1) Получаем URL случайной картинки кота
            r = await c.get(CAT_API_URL, headers={"User-Agent": "CatFactsApp/1.0"})
            r.raise_for_status()
            data = r.json()

            if not data or "url" not in data[0]:
                return Response(status_code=204)

            img_url = data[0]["url"]

            # 2) Скачиваем изображение и отдаём байты
            img = await c.get(img_url, headers={"User-Agent": "CatFactsApp/1.0"})
            ctype = (img.headers.get("content-type") or "image/jpeg").lower()

            if img.status_code != 200 or not img.content or not ctype.startswith("image/"):
                return Response(status_code=204)

            return Response(content=img.content, media_type=ctype, headers=no_cache_headers())

        except Exception:
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

