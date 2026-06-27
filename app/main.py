from fastapi import FastAPI

app = FastAPI(title="Spottr", description="An AI-powered lifting coach", version="0.1.0")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Hello, World!"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
