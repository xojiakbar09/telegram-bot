from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.sql import select
import os

# SQLite uchun URL
DATABASE_URL = "sqlite+aiosqlite:///anime_bot.db"

# Engine va Session yaratish
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class yaratish
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True)
    username = Column(String(100))
    full_name = Column(String(200))
    joined_date = Column(DateTime, default=datetime.utcnow)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(String(500))

class Anime(Base):
    __tablename__ = 'animes'
    
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    description = Column(String)
    genre = Column(String)
    country = Column(String)
    language = Column(String)
    code = Column(String, unique=True)
    image_url = Column(String)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

class Episode(Base):
    __tablename__ = 'episodes'
    
    id = Column(Integer, primary_key=True)
    anime_id = Column(Integer, ForeignKey('animes.id'))
    episode_number = Column(Integer)
    video_file_id = Column(String)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    username = Column(String)
    phone_number = Column(String)
    card_number = Column(String)
    vip_price = Column(Integer, default=50000)

class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True)
    channel_url = Column(String)
    channel_name = Column(String)
    added_date = Column(DateTime, default=datetime.now)

class VIPUser(Base):
    __tablename__ = 'vip_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True)
    is_vip = Column(Boolean, default=False)
    expire_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.now)

# Ma'lumotlar bazasi jadvallarini yaratish funksiyasi
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Ma'lumotlar bazasi sessiyasini yaratish uchun kontekst menejeri
async def get_session() -> AsyncSession:
    async with async_session() as session:
        return session

# Admin jadvalini tekshirish
async def check_admin_data():
    async with async_session() as session:
        admin = await session.execute(select(Admin).limit(1))
        admin = admin.scalar_one_or_none()
        
        if not admin:
            # Agar admin ma'lumotlari bo'lmasa, yangi admin qo'shish
            new_admin = Admin(
                card_number="8600123456789012",
                phone_number="+998901234567",
                vip_price=50000
            )
            session.add(new_admin)
            await session.commit()

# Funksiyalarni export qilish
__all__ = ['create_tables', 'get_session', 'check_admin_data', 'Base', 'User', 'Anime', 'Episode', 'Admin', 'Channel', 'VIPUser']
