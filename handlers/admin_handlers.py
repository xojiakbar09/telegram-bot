from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, FSInputFile
from database import async_session, Anime, Episode, Admin, User, VIPUser, Channel
import os
from sqlalchemy import select, delete, func
from sqlalchemy.sql import func
from datetime import datetime, timedelta
import aiohttp
import json

router = Router()

# Admin anime qo'shish holatlari
class AdminAnimeStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_genre = State()
    waiting_for_code = State()
    waiting_for_country = State()
    waiting_for_language = State()
    waiting_for_image = State()
    waiting_for_video = State()

class AdminStates(StatesGroup):
    waiting_for_vip_price = State()
    waiting_for_vip_days = State()
    waiting_for_user_id = State()
    waiting_for_user_id_remove = State()
    waiting_for_phone = State()
    waiting_for_card = State()
    waiting_for_channel = State()

@router.message(F.text == "panel")
async def admin_panel(message: types.Message):
    if str(message.from_user.id) in os.getenv("ADMINS", "").split(","):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ Anime qo'shish", callback_data="add_anime"),
                    InlineKeyboardButton(text="➕ Qism qo'shish", callback_data="add_episode")
                ],
                [
                    InlineKeyboardButton(text="👑 VIP sozlash", callback_data="vip_settings"),
                    InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")
                ],
                [
                    InlineKeyboardButton(text="🗑 O'chirish", callback_data="delete_anime"),
                    InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_anime")
                ]
            ]
        )
        await message.answer("👨‍💻 Admin panel\n\nQuyidagi amallardan birini tanlang:", reply_markup=keyboard)
    else:
        await message.answer("❌ Sizda admin huquqlari yo'q!")

@router.callback_query(F.data == "add_anime")
async def add_anime_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminAnimeStates.waiting_for_title)
    await callback.message.edit_text("🎬 Yangi anime qo'shish\n\nAnime nomini kiriting:")

@router.message(StateFilter(AdminAnimeStates.waiting_for_title))
async def process_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AdminAnimeStates.waiting_for_description)
    await message.answer("✍️ Anime haqida qisqacha ma'lumot kiriting:")

@router.message(StateFilter(AdminAnimeStates.waiting_for_description))
async def process_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AdminAnimeStates.waiting_for_genre)
    await message.answer("🎭 Anime janrini kiriting:")

@router.message(StateFilter(AdminAnimeStates.waiting_for_genre))
async def process_genre(message: types.Message, state: FSMContext):
    await state.update_data(genre=message.text)
    await state.set_state(AdminAnimeStates.waiting_for_code)
    await message.answer("🔢 Anime kodini kiriting (masalan: NAR001):")

@router.message(StateFilter(AdminAnimeStates.waiting_for_code))
async def process_code(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Anime).where(Anime.code == message.text)
        )
        if result.scalar_one_or_none():
            await message.answer("❌ Bu kod bilan anime mavjud! Boshqa kod kiriting:")
            return

    await state.update_data(code=message.text)
    await state.set_state(AdminAnimeStates.waiting_for_country)
    await message.answer("🌍 Anime davlatini kiriting:")

@router.message(StateFilter(AdminAnimeStates.waiting_for_country))
async def process_country(message: types.Message, state: FSMContext):
    await state.update_data(country=message.text)
    await state.set_state(AdminAnimeStates.waiting_for_language)
    await message.answer("🗣 Anime tilini kiriting:")

@router.message(StateFilter(AdminAnimeStates.waiting_for_language))
async def process_language(message: types.Message, state: FSMContext):
    await state.update_data(language=message.text)
    await state.set_state(AdminAnimeStates.waiting_for_image)
    await message.answer("🖼 Anime rasmini yuboring:")

@router.message(F.photo, StateFilter(AdminAnimeStates.waiting_for_image))
async def process_image(message: types.Message, state: FSMContext):
    photo = message.photo[-1]
    data = await state.get_data()
    
    # Post tayyorlash
    post_text = (
        f"📺 <b>{data['title']}</b>\n\n"
        f"📝 <i>{data['description']}</i>\n\n"
        f"🎭 Janr: {data['genre']}\n"
        f"🌍 Davlat: {data['country']}\n"
        f"🗣 Til: {data['language']}\n"
        f"🔢 Kod: <code>{data['code']}</code>"
    )
    
    # Post ko'rinishini ko'rsatish
    await message.answer_photo(
        photo=photo.file_id,
        caption=post_text,
        parse_mode="HTML"
    )
    
    # Tasdiqlash tugmalari
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_anime"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_anime")
            ]
        ]
    )
    
    await message.answer(
        "Post shunday ko'rinishda chiqadi.\n"
        "Tasdiqlaysizmi?",
        reply_markup=keyboard
    )
    
    # Rasmni state'ga saqlash
    await state.update_data(image_url=photo.file_id)

@router.callback_query(F.data == "confirm_anime")
async def confirm_anime(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    
    async with async_session() as session:
        new_anime = Anime(
            title=data['title'],
            description=data['description'],
            genre=data['genre'],
            code=data['code'],
            country=data['country'],
            language=data['language'],
            image_url=data['image_url'],
            views=0
        )
        
        session.add(new_anime)
        await session.commit()
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Qism qo'shish", callback_data=f"add_episode_{data['code']}"),
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
            ]
        ]
    )
    
    await callback.message.edit_text(
        "✅ Anime muvaffaqiyatli qo'shildi!\n\n"
        "Qism qo'shishni xohlaysizmi?",
        reply_markup=keyboard
    )
    
    await state.clear()

@router.callback_query(F.data == "cancel_anime")
async def cancel_anime(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "❌ Anime qo'shish bekor qilindi.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
            ]]
        )
    )

@router.callback_query(lambda c: c.data.startswith('add_episode_'))
async def add_episode_start(callback: types.CallbackQuery, state: FSMContext):
    anime_code = callback.data.split('_')[2]
    await state.update_data(anime_code=anime_code)
    await state.set_state(AdminAnimeStates.waiting_for_video)
    await callback.message.answer("🎬 Video faylni yuboring:")

@router.message(F.video, AdminAnimeStates.waiting_for_video)
async def process_video(message: types.Message, state: FSMContext):
    data = await state.get_data()
    anime_code = data['anime_code']
    
    async with async_session() as session:
        result = await session.execute(
            select(Anime).where(Anime.code == anime_code)
        )
        anime = result.scalar_one_or_none()
        
        if not anime:
            await message.answer("❌ Xatolik! Anime topilmadi.")
            await state.clear()
            return
        
        result = await session.execute(
            select(func.count(Episode.id)).where(Episode.anime_id == anime.id)
        )
        episode_count = result.scalar_one() + 1
        
        new_episode = Episode(
            anime_id=anime.id,
            episode_number=episode_count,
            video_file_id=message.video.file_id,
            views=0
        )
        
        session.add(new_episode)
        await session.commit()
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Yana qism qo'shish", callback_data=f"add_episode_{anime_code}"),
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
            ]
        ]
    )
    
    await message.answer(
        f"✅ {episode_count}-qism muvaffaqiyatli qo'shildi!\n\n"
        f"Yana qism qo'shish uchun tugmani bosing:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "delete_anime")
async def show_delete_anime_list(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Anime))
        animes = result.scalars().all()
        
        if not animes:
            await callback.message.edit_text(
                "❌ Hozircha animalar mavjud emas!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
                    ]]
                )
            )
            return
        
        keyboard = []
        for anime in animes:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑 {anime.title}", 
                    callback_data=f"confirm_delete_{anime.code}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
        ])
        
        await callback.message.edit_text(
            "🗑 O'chirish uchun animeni tanlang:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@router.callback_query(lambda c: c.data.startswith('confirm_delete_'))
async def confirm_delete_anime(callback: types.CallbackQuery):
    anime_code = callback.data.split('_')[2]
    
    async with async_session() as session:
        # Avval epizodlarni o'chirish
        anime = await session.execute(
            select(Anime).where(Anime.code == anime_code)
        )
        anime = anime.scalar_one_or_none()
        
        if anime:
            await session.execute(
                delete(Episode).where(Episode.anime_id == anime.id)
            )
            # So'ng animeni o'chirish
            await session.execute(
                delete(Anime).where(Anime.code == anime_code)
            )
            await session.commit()
            
            await callback.message.edit_text(
                "✅ Anime va uning barcha qismlari o'chirildi!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
                    ]]
                )
            )
        else:
            await callback.message.edit_text(
                "❌ Anime topilmadi!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
                    ]]
                )
            )

@router.callback_query(F.data == "show_stats")
async def show_statistics(callback: types.CallbackQuery):
    async with async_session() as session:
        # Umumiy statistika
        total_animes = await session.execute(select(func.count(Anime.id)))
        total_animes = total_animes.scalar()
        
        total_episodes = await session.execute(select(func.count(Episode.id)))
        total_episodes = total_episodes.scalar()
        
        total_views = await session.execute(
            select(func.sum(Anime.views))
        )
        total_views = total_views.scalar() or 0
        
        total_users = await session.execute(select(func.count(User.id)))
        total_users = total_users.scalar()
        
        vip_users = await session.execute(
            select(func.count(VIPUser.id)).where(VIPUser.is_vip == True)
        )
        vip_users = vip_users.scalar()
        
        # Top 5 anime
        top_animes = await session.execute(
            select(Anime).order_by(Anime.views.desc()).limit(5)
        )
        top_animes = top_animes.scalars().all()
        
        stats_text = (
            "📊 BOT STATISTIKASI\n\n"
            f"👥 Foydalanuvchilar: {total_users:,} ta\n"
            f"👑 VIP foydalanuvchilar: {vip_users:,} ta\n"
            f"📺 Jami animalar: {total_animes:,} ta\n"
            f"🎬 Jami qismlar: {total_episodes:,} ta\n"
            f"👁 Jami ko'rishlar: {total_views:,} ta\n\n"
            "🏆 TOP 5 ANIME:\n"
        )
        
        for i, anime in enumerate(top_animes, 1):
            stats_text += f"{i}. {anime.title} - {anime.views:,} ko'rish\n"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Yangilash", callback_data="show_stats"),
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
                ]
            ]
        )
        
        await callback.message.edit_text(stats_text, reply_markup=keyboard)

@router.callback_query(F.data == "vip_settings")
async def vip_settings(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 VIP narxini o'zgartirish", callback_data="change_vip_price"),
                InlineKeyboardButton(text="📱 Tel raqamni o'zgartirish", callback_data="add_phone")
            ],
            [
                InlineKeyboardButton(text="💳 Karta raqamini o'zgartirish", callback_data="add_card"),
                InlineKeyboardButton(text="👥 VIP foydalanuvchilar", callback_data="vip_users_list")
            ],
            [
                InlineKeyboardButton(text="➕ VIP berish", callback_data="give_vip"),
                InlineKeyboardButton(text="❌ VIP o'chirish", callback_data="remove_vip")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")
            ]
        ]
    )
    
    async with async_session() as session:
        admin = await session.execute(select(Admin).limit(1))
        admin = admin.scalar_one_or_none()
        
        if not admin:
            admin = Admin(
                vip_price=50000,
                username=callback.from_user.username  # Admin usernameni saqlash
            )
            session.add(admin)
            await session.commit()
        
        text = (
            "👨‍💻 VIP SOZLAMALARI\n\n"
            f"💰 VIP narxi: {admin.vip_price:,} so'm\n"
            f"💳 Karta: {admin.card_number or 'Kiritilmagan'}\n"
            f"📱 Tel: {admin.phone_number or 'Kiritilmagan'}"
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "change_vip_price")
async def change_vip_price(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_vip_price)
    await callback.message.edit_text(
        "💰 Yangi VIP narxini kiriting (so'mda):\n"
        "Masalan: 50000"
    )

@router.message(StateFilter(AdminStates.waiting_for_vip_price))
async def process_vip_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            await message.answer("❌ Narx 0 dan katta bo'lishi kerak!")
            return
        
        async with async_session() as session:
            admin = await session.execute(select(Admin).limit(1))
            admin = admin.scalar_one_or_none()
            
            if not admin:
                admin = Admin(vip_price=price)
                session.add(admin)
            else:
                admin.vip_price = price
            
            await session.commit()
        
        await message.answer(
            f"✅ VIP narxi {price:,} so'mga o'zgartirildi!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                ]]
            )
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting!")

@router.callback_query(F.data == "give_vip")
async def give_vip_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_user_id)
    await callback.message.edit_text(
        "👤 VIP berish uchun foydalanuvchi ID raqamini kiriting:\n"
        "Masalan: 123456789"
    )

@router.message(StateFilter(AdminStates.waiting_for_user_id))
async def process_vip_user(message: types.Message, state: FSMContext):
    try:
        user_id = int(message.text)
        await state.update_data(user_id=user_id)
        await state.set_state(AdminStates.waiting_for_vip_days)
        await message.answer("📅 VIP muddatini kiriting (kunlarda):\nMasalan: 30")
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting!")

@router.message(StateFilter(AdminStates.waiting_for_vip_days))
async def process_vip_days(message: types.Message, state: FSMContext):
    try:
        days = int(message.text)
        if days <= 0:
            await message.answer("❌ Kun soni 0 dan katta bo'lishi kerak!")
            return
        
        data = await state.get_data()
        user_id = data['user_id']
        expire_date = datetime.now() + timedelta(days=days)
        
        async with async_session() as session:
            vip_user = await session.execute(
                select(VIPUser).where(VIPUser.user_id == str(user_id))
            )
            vip_user = vip_user.scalar_one_or_none()
            
            if not vip_user:
                vip_user = VIPUser(
                    user_id=str(user_id),
                    is_vip=True,
                    expire_date=expire_date
                )
                session.add(vip_user)
            else:
                vip_user.is_vip = True
                vip_user.expire_date = expire_date
            
            await session.commit()
        
        await message.answer(
            f"✅ Foydalanuvchiga {days} kunlik VIP berildi!\n"
            f"VIP muddati: {expire_date.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                ]]
            )
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Iltimos, faqat raqam kiriting!")

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Anime qo'shish", callback_data="add_anime"),
                InlineKeyboardButton(text="➕ Qism qo'shish", callback_data="add_episode")
            ],
            [
                InlineKeyboardButton(text="👑 VIP sozlash", callback_data="vip_settings"),
                InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")
            ],
            [
                InlineKeyboardButton(text="🗑 O'chirish", callback_data="delete_anime"),
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_anime")
            ]
        ]
    )
    await callback.message.edit_text(
        "👨‍💻 Admin panel\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "remove_vip")
async def remove_vip_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_user_id_remove)
    await callback.message.edit_text(
        "❌ VIP o'chirish uchun foydalanuvchi ID raqamini kiriting:\n"
        "Masalan: 123456789"
    )

@router.message(StateFilter(AdminStates.waiting_for_user_id_remove))
async def process_remove_vip(message: types.Message, state: FSMContext):
    try:
        user_id = str(message.text)
        
        async with async_session() as session:
            result = await session.execute(
                select(VIPUser).where(VIPUser.user_id == user_id)
            )
            vip_user = result.scalar_one_or_none()
            
            if not vip_user:
                await message.answer(
                    "❌ Bu foydalanuvchi VIP emas!",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[[
                            InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                        ]]
                    )
                )
                await state.clear()
                return
            
            vip_user.is_vip = False
            vip_user.expire_date = None
            await session.commit()
            
            await message.answer(
                f"✅ Foydalanuvchi VIP huquqlari o'chirildi!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                    ]]
                )
            )
            
    except ValueError:
        await message.answer("❌ Noto'g'ri format! Iltimos, faqat raqam kiriting.")
    
    await state.clear()

@router.callback_query(F.data == "add_phone")
async def add_phone_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_phone)
    await callback.message.edit_text(
        "📱 Admin telefon raqamini kiriting:\n"
        "Masalan: +998901234567"
    )

@router.message(StateFilter(AdminStates.waiting_for_phone))
async def process_add_phone(message: types.Message, state: FSMContext):
    phone = message.text
    
    if not phone.startswith("+998") or not len(phone) == 13 or not phone[1:].isdigit():
        await message.answer(
            "❌ Noto'g'ri format! Raqamni +998XXXXXXXXX formatida kiriting."
        )
        return
    
    async with async_session() as session:
        admin = await session.execute(select(Admin).limit(1))
        admin = admin.scalar_one_or_none()
        
        if not admin:
            admin = Admin(phone_number=phone)
            session.add(admin)
        else:
            admin.phone_number = phone
        
        await session.commit()
        
        await message.answer(
            f"✅ Admin telefon raqami saqlandi: {phone}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                ]]
            )
        )
    
    await state.clear()

@router.callback_query(F.data == "vip_users_list")
async def show_vip_users(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(VIPUser).where(VIPUser.is_vip == True)
        )
        vip_users = result.scalars().all()
        
        if not vip_users:
            await callback.message.edit_text(
                "❌ Hozircha VIP foydalanuvchilar yo'q!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                    ]]
                )
            )
            return
        
        text = "👑 VIP FOYDALANUVCHILAR:\n\n"
        for user in vip_users:
            expire_date = user.expire_date.strftime("%d.%m.%Y %H:%M") if user.expire_date else "Muddatsiz"
            text += f"👤 ID: {user.user_id}\n"
            text += f"📅 Muddat: {expire_date}\n\n"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="🔄 Yangilash", callback_data="vip_users_list"),
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                ]
            ]
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "add_card")
async def add_card_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_card)
    await callback.message.edit_text(
        "💳 To'lov qabul qilish uchun karta raqamini kiriting:\n"
        "Masalan: 8600 1234 5678 9012"
    )

@router.message(StateFilter(AdminStates.waiting_for_card))
async def process_add_card(message: types.Message, state: FSMContext):
    card = message.text.replace(" ", "")  # Probellani olib tashlash
    
    if not card.isdigit() or len(card) != 16:
        await message.answer(
            "❌ Noto'g'ri format! Karta raqami 16 ta raqamdan iborat bo'lishi kerak."
        )
        return
    
    # Karta raqamini formatlash (har 4 ta raqamdan keyin probellar qo'shish)
    formatted_card = " ".join([card[i:i+4] for i in range(0, len(card), 4)])
    
    async with async_session() as session:
        admin = await session.execute(select(Admin).limit(1))
        admin = admin.scalar_one_or_none()
        
        if not admin:
            admin = Admin(card_number=formatted_card)
            session.add(admin)
        else:
            admin.card_number = formatted_card
        
        await session.commit()
        
        await message.answer(
            f"✅ Karta raqami saqlandi: {formatted_card}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="vip_settings")
                ]]
            )
        )
    
    await state.clear()

@router.message(Command("kanal"))
async def channel_settings_command(message: types.Message):
    if str(message.from_user.id) not in os.getenv("ADMINS", "").split(","):
        await message.answer("❌ Sizda admin huquqlari yo'q!")
        return
        
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel"),
                InlineKeyboardButton(text="🗑 Kanal o'chirish", callback_data="remove_channel")
            ],
            [
                InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="list_channels")
            ]
        ]
    )
    
    await message.answer(
        "📢 KANAL SOZLAMALARI\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "add_channel")
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_for_channel)
    await callback.message.edit_text(
        "📢 Yangi kanal qo'shish\n\n"
        "Kanal usernameni yuboring\n"
        "Masalan: @channel_username"
    )

@router.message(AdminStates.waiting_for_channel)
async def process_add_channel(message: types.Message, state: FSMContext):
    channel_username = message.text
    if not channel_username.startswith("@"):
        await message.answer("❌ Kanal username noto'g'ri formatda! @ bilan boshlangan username kiriting.")
        return
    
    try:
        # Kanal ma'lumotlarini olish
        channel = await bot.get_chat(channel_username)
        
        async with async_session() as session:
            # Kanal mavjudligini tekshirish
            existing_channel = await session.execute(
                select(Channel).where(Channel.channel_id == str(channel.id))
            )
            if existing_channel.scalar_one_or_none():
                await message.answer("❌ Bu kanal allaqachon qo'shilgan!")
                await state.clear()
                return
            
            # Yangi kanal qo'shish
            new_channel = Channel(
                channel_id=str(channel.id),
                channel_url=channel_username,
                channel_name=channel.title
            )
            session.add(new_channel)
            await session.commit()
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="list_channels")]
            ]
        )
        
        await message.answer(
            f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
            f"📢 Kanal: {channel.title}\n"
            f"🔗 Username: {channel_username}",
            reply_markup=keyboard
        )
    except Exception as e:
        await message.answer(
            "❌ Xatolik yuz berdi!\n\n"
            "Sabablari:\n"
            "• Kanal topilmadi\n"
            "• Kanal username noto'g'ri"
        )
    
    await state.clear()

@router.callback_query(F.data == "list_channels")
async def list_channels(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(select(Channel))
        channels = result.scalars().all()
        
        if not channels:
            await callback.message.edit_text(
                "❌ Hozircha kanallar qo'shilmagan!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")
                    ]]
                )
            )
            return
        
        text = "📢 KANALLAR RO'YXATI:\n\n"
        keyboard = []
        
        for i, channel in enumerate(channels, 1):
            text += f"{i}. {channel.channel_name}\n"
            text += f"└ {channel.channel_url}\n\n"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🗑 {channel.channel_name}ni o'chirish", 
                    callback_data=f"delete_channel_{channel.channel_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_channel")
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@router.callback_query(lambda c: c.data.startswith('delete_channel_'))
async def delete_channel(callback: types.CallbackQuery):
    channel_id = callback.data.split('_')[2]
    
    async with async_session() as session:
        await session.execute(
            delete(Channel).where(Channel.channel_id == channel_id)
        )
        await session.commit()
        
        await callback.message.edit_text(
            "✅ Kanal muvaffaqiyatli o'chirildi!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="📋 Kanallar ro'yxati", callback_data="list_channels")
                ]]
            )
        )

# Yangi funksiyalar... 