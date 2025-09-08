# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx, random

app = FastAPI()

CATFACT_URL = "https://catfact.ninja/fact"
GT_URL = "https://translate.googleapis.com/translate_a/single"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"

async def gtr(client: httpx.AsyncClient, text: str, tl: str) -> str:
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

@app.get("/fact")
async def get_fact(lang: str = "en"):
    async with httpx.AsyncClient() as c:
        fact = (await c.get(CATFACT_URL, timeout=5)).json()["fact"]
        if lang.lower().startswith("ru"):
            fact = await gtr(c, fact, "ru")
    return {"fact": fact}

# ❱❱❱ Новый эндпоинт: редирект на случайную картинку кота с Wikimedia Commons
@app.get("/catimg")
async def catimg():
    params = {
        "action": "query",
        "generator": "categorymembers",
        "gcmtitle": "Category:Felis catus",  # категория с фото домашних кошек
        "gcmnamespace": "6",                 # файлы
        "gcmlimit": "50",
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": "1200",
        "format": "json",
    }
    async with httpx.AsyncClient() as c:
        r = await c.get(COMMONS_API, params=params, timeout=8)
        pages = (r.json().get("query") or {}).get("pages") or {}
        items = list(pages.values())
        if not items:
            # запасной вариант (редко)
            return RedirectResponse("https://upload.wikimedia.org/wikipedia/commons/3/3a/Cat03.jpg")
        page = random.choice(items)
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        return RedirectResponse(url)

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

    function newCat() {
      // добавляем ?ts=... чтобы обойти кэш
      img.src = "/catimg?ts=" + Date.now();
    }

    // при загрузке страницы — сразу показать кота
    newCat();

    async function loadFact() {
      factBox.textContent = 'Загрузка...';
      newCat(); // и картинку обновим
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



