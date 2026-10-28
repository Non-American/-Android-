from fastapi import FastAPI
from pydantic import BaseModel, Field

from .embeddings import load_model

app = FastAPI(title="Orbita embedder")
model = load_model()


class Req(BaseModel):
    tags: list[str] = Field(min_length=1, max_length=50)


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/embed")
def embed(req: Req):
    return {"vectors": model.encode([t[:100] for t in req.tags]).tolist()}
