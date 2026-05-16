from fastapi import FastAPI
from engine.router import get_best_spot

app = FastAPI()

@app.get("/surf")
def surf():
    return get_best_spot()