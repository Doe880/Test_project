# main.py
from fastapi import FastAPI
import httpx

app = FastAPI()

CATFACT_URL = "https://catfact.ninja/fact"
GT_URL = "https://translate.googleapis.com/translate_a/single"

@app.get("/healthz")
def health():
    return {"status": "ok"}

async def translate_lazy(client: httpx.AsyncClient, text: str, tl: str) -> str:
    try:
        r = await client.get(
            GT_URL,
            params={"client": "gtx", "sl": "en", "tl": tl, "dt": "t", "q": text},
            timeout=5,
        )
        if r.status_code == 200:
            data = r.json()
            return "".join(seg[0] for seg in data[0] if seg and seg[0])
    except Exception:
        pass
    return text  # фолбэк: оставляем оригинал

@app.get("/fact")
async def get_fact(lang: str = "en"):
    async with httpx.AsyncClient() as c:
        try:
            fact = (await c.get(CATFACT_URL, timeout=5)).json()["fact"]
        except Exception:
            # хостинг без выхода в интернет → вернём статичную заглушку
            fact = "Cats sleep 12–16 hours a day."

        if lang.lower().startswith("ru"):
            fact = await translate_lazy(c, fact, "ru")

    return {"fact": fact}
