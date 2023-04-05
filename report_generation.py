# report_generation.py
import datetime
import pytz
import pandas as pd
from typing import Dict
from sqlalchemy.orm import Session
from database import Store, StoreStatus, StoreBusinessHours, engine
from concurrent.futures import ThreadPoolExecutor,as_completed
import asyncio
from tqdm import tqdm  

async def update_progress_bar(progress_bar, tasks):
    completed_count = 0
    while completed_count < len(tasks):
        completed_count = sum(1 for task in tasks if task.done())
        progress_bar.update(completed_count - progress_bar.n)
        await asyncio.sleep(1)
    progress_bar.close()


def process_store(store_id, store_timezone, session):
    # Query only the relevant store_statuses and store_business_hours for this store
    store_statuses = session.query(StoreStatus).filter(StoreStatus.store_id == store_id).all()
    store_business_hours = session.query(StoreBusinessHours).filter(StoreBusinessHours.store_id == store_id).all()

    local_timezone = pytz.timezone(store_timezone)

    # Calculate the uptime and downtime within business hours
    uptime_last_hour, downtime_last_hour, uptime_last_day, downtime_last_day, uptime_last_week, downtime_last_week = calculate_uptime_downtime(
        store_statuses, store_business_hours, store_id, local_timezone
    )

    return {
        "store_id": store_id,
        "uptime_last_hour": uptime_last_hour,
        "downtime_last_hour": downtime_last_hour,
        "uptime_last_day": uptime_last_day,
        "downtime_last_day": downtime_last_day,
        "uptime_last_week": uptime_last_week,
        "downtime_last_week": downtime_last_week
    }

async def generate_report(report_id: str, reports: Dict[str, str]):
    session = Session(bind=engine)

    # Retrieve store data from the database
    stores = session.query(Store).all()

    # Process data and generate the report
    result = []

    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=10) as executor: 
        tasks = [loop.run_in_executor(executor, process_store, store.id, store.timezone_str, session) for store in stores]

        # Add progress bar with tqdm
        progress_bar = tqdm(total=len(tasks), desc=f"Generating Report {report_id}", ncols=100)

        progress_bar_updater = asyncio.create_task(update_progress_bar(progress_bar, tasks))

        completed_tasks, _ = await asyncio.wait(tasks)
        await progress_bar_updater

    for task in completed_tasks:
        result.append(task.result())

    # Save the report as a CSV file
    result_df = pd.DataFrame(result)
    result_df.to_csv(f"reports/{report_id}.csv", index=False)

    reports[report_id] = "Complete"

    session.close()



def calculate_uptime_downtime(store_statuses, store_business_hours, store_id, local_timezone):
    # Define the time intervals for the report
    now = datetime.datetime.now(local_timezone)
    last_hour = now - datetime.timedelta(hours=1)
    last_day = now - datetime.timedelta(days=1)
    last_week = now - datetime.timedelta(weeks=1)

    # Filter the store statuses for the current store
    filtered_store_statuses = [status for status in store_statuses if status.store_id == store_id]

    # Calculate the uptime and downtime within business hours
    uptime_last_hour, downtime_last_hour = get_uptime_downtime(filtered_store_statuses, store_business_hours, store_id, last_hour, now, local_timezone)
    uptime_last_day, downtime_last_day = get_uptime_downtime(filtered_store_statuses, store_business_hours, store_id, last_day, now, local_timezone)
    uptime_last_week, downtime_last_week = get_uptime_downtime(filtered_store_statuses, store_business_hours, store_id, last_week, now, local_timezone)

    return uptime_last_hour, downtime_last_hour, uptime_last_day, downtime_last_day, uptime_last_week, downtime_last_week


def get_uptime_downtime(store_statuses, store_business_hours, store_id, start_time, end_time, local_timezone):
    # Initialize uptime and downtime counters
    uptime_minutes = 0
    downtime_minutes = 0

    # Find the store's business hours
    store_hours = [hour for hour in store_business_hours if hour.store_id == store_id]

    # If the store does not have business hours data, assume it's open 24*7
    if not store_hours:
        store_hours.append(StoreBusinessHours(
            day_of_week=list(range(0, 7)),
            start_time_local="00:00:00",
            end_time_local="23:59:59"
        ))

    # Iterate through each day within the desired time interval
    current_day = start_time.date()
    while current_day <= end_time.date():
        for hour in store_hours:
            day_of_week = current_day.weekday()

            # Check if the current day is within the store's business hours
            if (type( hour.day_of_week)==int and day_of_week == hour.day_of_week) or (type( hour.day_of_week)==list and day_of_week in hour.day_of_week):
                start_time_local = datetime.datetime.strptime(hour.start_time_local, "%H:%M:%S").time()
                end_time_local = datetime.datetime.strptime(hour.end_time_local, "%H:%M:%S").time()

                business_start = local_timezone.localize(datetime.datetime.combine(current_day, start_time_local))
                business_end = local_timezone.localize(datetime.datetime.combine(current_day, end_time_local))

                # Clip the business hours to the desired time interval
                business_start = max(business_start, start_time)
                business_end = min(business_end, end_time)

                if business_start < business_end:
                    # Find the last status observation before the start of the time interval
                    previous_status = None
                    for status in reversed(store_statuses):
                        if status.timestamp_utc.replace(tzinfo=pytz.utc) < business_start.astimezone(pytz.utc):
                            previous_status = status.status
                            break

                    previous_timestamp = business_start

                    for status in store_statuses:
                        # Convert the timestamp to the local timezone
                        timestamp_local = status.timestamp_utc.replace(tzinfo=pytz.utc).astimezone(local_timezone)

                        # Check if the status is within the current business hours
                        if business_start <= timestamp_local <= business_end:
                            if previous_status is not None:
                                delta_minutes = (timestamp_local - previous_timestamp).total_seconds() / 60

                                if previous_status == "active":
                                    uptime_minutes += delta_minutes
                                else:
                                    downtime_minutes += delta_minutes

                            previous_status = status.status
                            previous_timestamp = timestamp_local

                    # Add the remaining time after the last status observation
                    if previous_status is not None:
                        delta_minutes = (business_end - previous_timestamp).total_seconds() / 60

                        if previous_status == "active":
                            uptime_minutes += delta_minutes
                        else:
                            downtime_minutes += delta_minutes

        current_day += datetime.timedelta(days=1)

    return uptime_minutes, downtime_minutes
