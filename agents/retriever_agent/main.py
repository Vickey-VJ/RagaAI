from fastapi import FastAPI, Body
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

app = FastAPI()
model = SentenceTransformer('all-MiniLM-L6-v2')
index = faiss.IndexFlatL2(384)
corpus = []

@app.post("/add")
def add_texts(texts: list[str] = Body(...)):
    global corpus
    embeddings = model.encode(texts)
    index.add(np.array(embeddings))
    corpus.extend(texts)
    return {"added": len(texts)}

@app.get("/search")
def search(query: str):
    embedding = model.encode([query])
    D, I = index.search(np.array(embedding), k=3)
    return {"results": [corpus[i] for i in I[0]]}