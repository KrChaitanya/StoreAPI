# import_data.py
import pandas as pd
from sqlalchemy.orm import Session

from database import Store, StoreStatus, StoreBusinessHours, engine
import datetime
def import_data():
    session = Session(bind=engine)

    # Import store status data
    store_status_df = pd.read_csv('store_status.csv')
    print("Store status data:")
    print(store_status_df.head())
    for idx, row in store_status_df.iterrows():
        store_status = StoreStatus(store_id=row['store_id'], timestamp_utc=datetime.datetime.fromisoformat(row['timestamp_utc'].strip("UTC").strip()), status=row['status'])
        session.add(store_status)

    # Import store business hours data
    store_business_hours_df = pd.read_csv('store_business_hours.csv')
    print("\nStore business hours data:")
    print(store_business_hours_df.head())
    for idx, row in store_business_hours_df.iterrows():
        store_business_hour = StoreBusinessHours(
            store_id=row['store_id'],
            day_of_week=row['day'],
            start_time_local=row['start_time_local'],
            end_time_local=row['end_time_local']
        )
        session.add(store_business_hour)

    # Import store timezone data
    store_timezone_df = pd.read_csv('store_timezone.csv')
    print("\nStore timezone data:")
    print(store_timezone_df.head())
    for idx, row in store_timezone_df.iterrows():
        store = Store(id=row['store_id'], timezone_str=row['timezone_str'])
        session.add(store)

    print("\nCommitting changes to the database...")
    session.commit()
    session.close()
    print("Data import complete.")

if __name__ == "__main__":
    import_data()

