import uvicorn
from app.main import app  # noqa: F401 — re-exported so `uvicorn main:app` works

if __name__ == "__main__":
    uvicorn.run("app.main:app", port=8000, reload=True)
