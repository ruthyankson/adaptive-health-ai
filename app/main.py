from fastapi import FastAPI

app = FastAPI(title="Adaptive Health AI")

@app.get("/health")
def health():
    return {"status": "ok"}