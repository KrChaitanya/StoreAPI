# main.py
from fastapi import FastAPI
from report import router as report_router

app = FastAPI()

app.include_router(report_router, prefix="/report", tags=["report"])

@app.get("/")
def read_root():
    return {"Hello": "World"}

