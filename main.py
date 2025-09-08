# main.py
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

CATFACT_URL = "https://catfact.ninja/fact"
GT_URL = "https://translate.googleapis.com/translate_a/single"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


async def gtr(client: httpx.AsyncClient, text: str, tl: str) -> str:
    """Ленивый перевод через неофициальный Google Translate; фолбэк — исходный текст."""
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
        try:
            fact = (await c.get(CATFACT_URL, timeout=5)).json()["fact"]
        except Exception:
            fact = "Cats sleep 12–16 hours a day."  # запасной вариант
        if lang.lower().startswith("ru"):
            fact = await gtr(c, fact, "ru")
    return {"fact": fact}


@app.get("/catimg")
async def catimg():
    """Проксирование случайной картинки кота из Wikimedia Commons + запрет кэша."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=10) as c:
        try:
            # 1) Случайный файл из пространства файлов (ns=6)
            r1 = await c.get(COMMONS_API, params={
                "action": "query",
                "list": "random",
                "rnnamespace": "6",
                "rnlimit": "1",
                "format": "json",
            })
            rnd = (r1.json().get("query") or {}).get("random") or []
            title = rnd[0]["title"] if rnd else None
            if not title:
                raise RuntimeError("no random file")

            # 2) Получаем прямой URL уменьшенной копии
            r2 = await c.get(COMMONS_API, params={
                "action": "query",
                "titles": title,
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "iiurlwidth": "1200",
                "format": "json",
            })
            pages = (r2.json().get("query") or {}).get("pages") or {}
            info = next(iter(pages.values()), {})
            ii = (info.get("imageinfo") or [{}])[0]
            img_url = ii.get("thumburl") or ii.get("url")
            if not img_url:
                raise RuntimeError("no image url")

            # 3) Качаем и отдаём байты с заголовками no-cache
            img = await c.get(img_url)
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
        except Exception:
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
      // анти-кэш параметр
      img.src = "/catimg?ts=" + Date.now();
    }

    // показать кота при загрузке
    newCat();

    async function loadFact() {
      factBox.textContent = 'Загрузка...';
      newCat(); // обновим картинку
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




