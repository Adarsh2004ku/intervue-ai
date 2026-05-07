from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Intervue AI Running"}


@app.get("/health")
async def health():
    return {"status": "ok"}