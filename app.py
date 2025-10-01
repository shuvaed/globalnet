from fastapi import FastAPI, Request

app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

@app.post("/echo")
async def echo(req: Request):
    data = await req.json()
    return {"you_sent": data}
