from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from database import Session, Anime

class AnimeForm(StatesGroup):
    title = State()
    description = State()
    genre = State()
    episodes = State()
    status = State()
    image = State()

async def add_anime_start(message: types.Message, state: FSMContext):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )
    await message.answer("Anime nomini kiriting:", reply_markup=keyboard)
    await state.set_state(AnimeForm.title)

async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await message.answer("Anime haqida qisqacha ma'lumot kiriting:")
    await state.set_state(AnimeForm.description)

async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    genre_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Action"), KeyboardButton(text="Adventure")],
            [KeyboardButton(text="Comedy"), KeyboardButton(text="Drama")],
            [KeyboardButton(text="Fantasy"), KeyboardButton(text="Horror")],
            [KeyboardButton(text="Mystery"), KeyboardButton(text="Romance")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Anime janrini tanlang:", reply_markup=genre_keyboard)
    await state.set_state(AnimeForm.genre)

async def process_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await message.answer("Anime qismlar sonini kiriting (raqamda):")
    await state.set_state(AnimeForm.episodes)

async def process_episodes(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Iltimos, faqat raqam kiriting!")
        return
    
    await state.update_data(episodes=int(message.text))
    
    status_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Tugallangan"), KeyboardButton(text="Davom etmoqda")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Anime holatini tanlang:", reply_markup=status_keyboard)
    await state.set_state(AnimeForm.status)

async def process_status(message: types.Message, state: FSMContext):
    await state.update_data(status=message.text)
    await message.answer("Anime rasmini yuklang:")
    await state.set_state(AnimeForm.image)

async def process_image(message: types.Message, state: FSMContext):
    if not message.photo:
        await message.answer("Iltimos, rasm yuklang!")
        return
    
    data = await state.get_data()
    data['image_url'] = message.photo[-1].file_id
    
    # Ma'lumotlarni bazaga saqlash
    session = Session()
    new_anime = Anime(
        title=data['title'],
        description=data['description'],
        genre=data['genre'],
        episodes=data['episodes'],
        status=data['status'],
        image_url=data['image_url']
    )
    session.add(new_anime)
    session.commit()
    session.close()
    
    await state.clear()
    main_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Anime qo'shish"), KeyboardButton(text="🔎 Anime izlash")]
        ],
        resize_keyboard=True
    )
    
    await message.answer("Anime muvaffaqiyatli qo'shildi!", reply_markup=main_keyboard)

async def cancel_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    main_keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎥 Anime qo'shish"), KeyboardButton(text="🔎 Anime izlash")]
        ],
        resize_keyboard=True
    )
    await message.answer("Bekor qilindi!", reply_markup=main_keyboard) 