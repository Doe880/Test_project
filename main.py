# main.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import httpx

app = FastAPI()

CATFACT_URL = "https://catfact.ninja/fact"
GT_URL = "https://translate.googleapis.com/translate_a/single"

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

    // при загрузке страницы — сразу новый кот
    img.src = "https://cataas.com/cat?width=600&height=400&timestamp=" + Date.now();

    async function loadFact() {
      factBox.textContent = 'Загрузка...';
      // каждый раз новый кот
      img.src = "https://cataas.com/cat?width=600&height=400&timestamp=" + Date.now();
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

