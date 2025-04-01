from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from datetime import datetime
from sqlalchemy.sql import select

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
    title = Column(String(200), nullable=False)
    description = Column(Text)
    genre = Column(String(100))
    code = Column(String(50), unique=True)
    country = Column(String(100))
    language = Column(String(50))
    image_url = Column(String(500))
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Episode(Base):
    __tablename__ = 'episodes'
    
    id = Column(Integer, primary_key=True)
    anime_id = Column(Integer, ForeignKey('animes.id'))
    episode_number = Column(Integer)
    video_file_id = Column(String(500))
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Admin(Base):
    __tablename__ = 'admins'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    card_number = Column(String, nullable=True)
    vip_price = Column(Integer, default=50000)
    studio_name = Column(String(200))

class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String(100), unique=True)
    title = Column(String(200))
    required = Column(Boolean, default=True)

class VIPUser(Base):
    __tablename__ = 'vip_users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(100), unique=True)
    is_vip = Column(Boolean, default=False)
    expire_date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    payment_amount = Column(Integer)
    payment_date = Column(DateTime)

# Database engine va session yaratish
engine = create_async_engine(
    'sqlite+aiosqlite:///anime_database.db',
    echo=True
)

async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Database yaratish uchun funksiya
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)  # Eski bazani o'chirish
        await conn.run_sync(Base.metadata.create_all)  # Yangi baza yaratish

# Session olish uchun funksiya
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
