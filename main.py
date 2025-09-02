# main.py
from fastapi import FastAPI
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
            # ответ — массив сегментов; склеим перевод
            return "".join(seg[0] for seg in data[0] if seg and seg[0])
    except Exception:
        pass
    return text  # фолбэк: вернём оригинал

@app.get("/fact")
async def get_fact(lang: str = "en"):
    async with httpx.AsyncClient() as c:
        fact = (await c.get(CATFACT_URL, timeout=5)).json()["fact"]
        if lang.lower().startswith("ru"):
            fact = await gtr(c, fact, "ru")
    return {"fact": fact}
