# database.py
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey,Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

DATABASE_URL = "sqlite:///./store_data.db"

engine = create_engine(DATABASE_URL)
Base = declarative_base()

class StoreStatus(Base):
    __tablename__ = "store_statuses"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    timestamp_utc = Column(DateTime)
    
    status = Column(String)

    store = relationship("Store", back_populates="store_statuses")
    store_id_idx = Index('store_id_idx', store_id)


class StoreBusinessHours(Base):
    __tablename__ = "store_business_hours"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, ForeignKey("stores.id"))
    day_of_week = Column(Integer)
    start_time_local = Column(String)
    end_time_local = Column(String)

    store = relationship("Store", back_populates="store_business_hours")
    store_id_idx = Index('store_id_idx', store_id)
    


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    timezone_str = Column(String, default="America/Chicago")

    store_statuses = relationship("StoreStatus", back_populates="store")
    store_business_hours = relationship("StoreBusinessHours", back_populates="store")


Base.metadata.create_all(bind=engine)

