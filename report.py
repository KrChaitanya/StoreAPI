# report.py
import uuid
from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from typing import Dict
import asyncio

from database import Store, StoreStatus, StoreBusinessHours, engine
from report_generation import generate_report

router = APIRouter()

reports: Dict[str, str] = {}
report_queue: asyncio.Queue = asyncio.Queue()

@router.post("/trigger_report")
async def trigger_report():
    report_id = str(uuid.uuid4())
    reports[report_id] = "Running"
    report_queue.put_nowait(report_id)
    asyncio.ensure_future(queue_processor())
    return {"report_id": report_id}

@router.get("/get_report/{report_id}")
def get_report(report_id: str):
    if report_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")

    status = reports[report_id]
    if status == "Complete":
        with open(f"reports/{report_id}.csv", "r") as csv_file:
            csv_content = csv_file.read()
        return {"status": "Complete", "csv_file": csv_content}
    else:
        return {"status": "Running"}

async def queue_processor():
    while not report_queue.empty():
        report_id = await report_queue.get()
        await generate_report(report_id, reports)
        report_queue.task_done()

