from aiogram import Router, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database import async_session, Anime, VIPUser, Admin, Episode, Channel
from states.states import AnimeStates
from utils.api_client import get_anime_info
from datetime import datetime, timedelta
from sqlalchemy import select
import os
from collections import defaultdict
from typing import Dict, List

router = Router()

# Foydalanuvchilar xabarlarini kuzatish uchun dictionary
user_messages: Dict[int, List[datetime]] = defaultdict(list)
# Bloklangan foydalanuvchilar va ularning blok vaqti
blocked_users: Dict[int, datetime] = {}

# Xabarlarni tekshirish funksiyasi
async def check_message_limit(user_id: int) -> bool:
    current_time = datetime.now()
    
    # Agar foydalanuvchi bloklangan bo'lsa
    if user_id in blocked_users:
        if current_time < blocked_users[user_id]:
            remaining_time = int((blocked_users[user_id] - current_time).total_seconds())
            return False, remaining_time
        else:
            # Blokdan chiqarish
            del blocked_users[user_id]
            user_messages[user_id].clear()
    
    # 5 soniyadan eski xabarlarni o'chirish
    user_messages[user_id] = [
        msg_time for msg_time in user_messages[user_id]
        if current_time - msg_time <= timedelta(seconds=5)
    ]
    
    # Yangi xabarni qo'shish
    user_messages[user_id].append(current_time)
    
    # 5 soniya ichida 5 tadan ko'p xabar tekshirish
    if len(user_messages[user_id]) > 5:
        # Foydalanuvchini 20 soniyaga bloklash
        blocked_users[user_id] = current_time + timedelta(seconds=20)  # 50 soniya o'rniga 20 soniya
        return False, 20  # 50 o'rniga 20 qaytaramiz
    
    return True, 0

# Xar bir xabar uchun middleware
@router.message()
async def message_handler(message: types.Message):
    can_send, wait_time = await check_message_limit(message.from_user.id)
    
    if not can_send:
        await message.answer(
            f"❌ Siz juda ko'p so'rov jo'natdingiz!\n"
            f"⏳ Iltimos, {wait_time} soniyadan keyin qayta urinib ko'ring."
        )
        return False
    
    # Agar cheklovlar o'tsa, xabarni keyingi handlerga o'tkazish
    return True

class SearchForm(StatesGroup):
    query = State()
    code = State()

class UserStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_name = State()

@router.message(Command("start"))
async def start_command(message: types.Message):
    # Obuna tekshirish
    if not await check_subscription(message.from_user.id):
        text = (
            "👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:\n\n"
            "Obuna bo'lgach, \"✅ Tekshirish\" tugmasini bosing!"
        )
        keyboard = await get_channels_keyboard()
        await message.answer(text, reply_markup=keyboard)
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Anime qidirish", callback_data="search"),
                InlineKeyboardButton(text="🔢 Kod orqali", callback_data="search_by_code")
            ],
            [
                InlineKeyboardButton(text="📺 Trenddagi animalar", callback_data="trending"),
                InlineKeyboardButton(text="👑 VIP bo'lish", callback_data="vip")
            ],
            [
                InlineKeyboardButton(text="📢 Reklama va homiylik", callback_data="ads_sponsor")
            ]
        ]
    )
    
    await message.answer(
        f"👋 Salom, {message.from_user.first_name}!\n\n"
        "🎬 Anime botga xush kelibsiz!\n"
        "Bu bot orqali siz:\n"
        "• Anime qidirishingiz\n"
        "• Ma'lumotlarni ko'rishingiz\n"
        "• Epizodlarni yuklab olishingiz mumkin!\n\n"
        "Boshlash uchun quyidagi tugmalardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "search")
async def search_menu(callback: types.CallbackQuery):
    # Obuna tekshirish
    if not await check_subscription(callback.from_user.id):
        text = "👋 Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:"
        keyboard = await get_channels_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard)
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Nom bo'yicha", callback_data="search_by_name"),
                InlineKeyboardButton(text="🔢 Kod bo'yicha", callback_data="search_by_code")
            ],
            [
                InlineKeyboardButton(text="🎭 Janr bo'yicha", callback_data="search_by_genre"),
                InlineKeyboardButton(text="📺 Barcha animalar", callback_data="show_all_animes")
            ],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
        ]
    )
    
    await callback.message.edit_text(
        "🔍 Anime qidirish usulini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "search_by_name")
async def search_by_name(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 Anime nomini kiriting:"
    )
    await state.set_state(AnimeStates.waiting_for_search)

@router.callback_query(F.data == "trending")
async def show_trending(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Anime).order_by(Anime.views.desc()).limit(10)
        )
        trending_animes = result.scalars().all()
        
        text = "📈 Eng ko'p ko'rilgan TOP-10 anime:\n\n"
        keyboard = []
        
        for anime in trending_animes:
            text += f"🎬 {anime.title}\n"
            text += f"👁 {anime.views} marta ko'rilgan\n"
            text += f"🎭 Janr: {anime.genre}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{anime.title}", 
                    callback_data=f"anime_{anime.code}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@router.callback_query(F.data == "vip")
async def show_vip_info(callback: types.CallbackQuery):
    async with async_session() as session:
        # Admin ma'lumotlarini olish
        admin = await session.execute(select(Admin).limit(1))
        admin = admin.scalar_one_or_none()
        
        if not admin:
            await callback.message.edit_text(
                "❌ To'lov ma'lumotlari hali sozlanmagan!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")
                    ]]
                )
            )
            return
        
        vip_price = admin.vip_price or 50000
        card_number = admin.card_number
        phone_number = admin.phone_number
        admin_username = admin.username or "admin"
        
        text = (
            "👑 VIP OBUNA\n\n"
            "VIP obuna orqali quyidagi imkoniyatlarga ega bo'lasiz:\n"
            "• Cheksiz anime ko'rish\n"
            "• Reklamasiz foydalanish\n"
            "• Yuqori sifatli videolar\n"
            "• Maxsus anime tavsiyalar\n\n"
            f"💰 Narx: {vip_price:,} so'm/oyiga\n\n"
            "💳 To'lov uchun:\n"
        )
        
        if card_number:
            text += f"Karta: <code>{card_number}</code>\n"
        
        if phone_number:
            text += f"📱 Tel: {phone_number}\n"
        
        text += "\n✅ To'lov qilgach, adminga murojaat qiling."
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📞 Admin", url=f"https://t.me/{admin_username}"),
                    InlineKeyboardButton(text="📋 Karta raqamini nusxalash", callback_data=f"copy_card_{card_number}" if card_number else "no_card")
                ],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
            ]
        )
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

@router.callback_query(lambda c: c.data == "no_card")
async def no_card_handler(callback: types.CallbackQuery):
    await callback.answer("❌ Karta raqami hali kiritilmagan!", show_alert=True)

@router.callback_query(F.data == "help")
async def show_help(callback: types.CallbackQuery):
    text = (
        "ℹ️ BOT YORDAM\n\n"
        "Bot buyruqlari:\n"
        "/start - Botni ishga tushirish\n"
        "/search - Anime qidirish\n"
        "/help - Yordam\n\n"
        "Qo'shimcha funksiyalar:\n"
        "• Anime nomi orqali qidirish\n"
        "• Anime kodi orqali qidirish\n"
        "• Janr bo'yicha qidirish\n"
        "• Tasodifiy anime\n"
        "• VIP obuna\n\n"
        "Muammo yuzaga kelsa, @admin ga murojaat qiling."
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Anime qidirish", callback_data="search"),
                InlineKeyboardButton(text="🔢 Kod orqali", callback_data="search_by_code")
            ],
            [
                InlineKeyboardButton(text="📺 Trenddagi animalar", callback_data="trending"),
                InlineKeyboardButton(text="👑 VIP bo'lish", callback_data="vip")
            ]
        ]
    )
    
    await callback.message.edit_text(
        f"🎬 Asosiy menyu\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=keyboard
    )

# Anime qidirish uchun handler
@router.message(AnimeStates.waiting_for_search)
async def process_anime_search(message: types.Message, state: FSMContext):
    search_query = message.text.strip()  # Bo'sh joylarni olib tashlash
    
    async with async_session() as session:
        # Anime nomini aniq tekshirish
        result = await session.execute(
            select(Anime).where(Anime.title.ilike(f"{search_query}"))
        )
        anime = result.scalar_one_or_none()
        
        if not anime:
            # Agar aniq nom topilmasa
            await message.answer(
                "❌ Bunday nomli anime mavjud emas!\n\n"
                "Iltimos, anime nomini to'g'ri kiriting.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="search")
                    ]]
                )
            )
        else:
            # Epizodlar sonini olish
            episodes = await session.execute(
                select(Episode).where(Episode.anime_id == anime.id).order_by(Episode.episode_number)
            )
            episodes = episodes.scalars().all()
            
            # Epizod tugmalarini yaratish
            keyboard = []
            row = []
            for episode in episodes:
                row.append(
                    InlineKeyboardButton(
                        text=f"📺 {episode.episode_number}-qism",
                        callback_data=f"watch_{anime.code}_{episode.episode_number}"
                    )
                )
                if len(row) == 2:  # 2 tadan qilib joylashtirish
                    keyboard.append(row)
                    row = []
            
            if row:  # Qolgan tugmalarni qo'shish
                keyboard.append(row)
            
            # Qo'shimcha tugmalar
            keyboard.append([
                InlineKeyboardButton(text="⬇️ Hammasini yuklash", callback_data=f"download_all_{anime.code}")
            ])
            keyboard.append([
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="search")
            ])
            
            # Anime ma'lumotlarini yuborish
            await message.answer_photo(
                photo=anime.image_url,
                caption=(
                    f"📺 <b>{anime.title}</b>\n\n"
                    f"📝 <i>{anime.description}</i>\n\n"
                    f"🎭 Janr: {anime.genre}\n"
                    f"🌍 Davlat: {anime.country}\n"
                    f"🗣 Til: {anime.language}\n"
                    f"🔢 Kod: <code>{anime.code}</code>\n"
                    f"👁 Ko'rilgan: {anime.views:,} marta\n\n"
                    f"📺 Mavjud qismlar soni: {len(episodes)} ta"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
            
            # Ko'rishlar sonini oshirish
            anime.views += 1
            await session.commit()
    
    await state.clear()

async def show_main_menu(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔍 Anime izlash"), KeyboardButton(text="👑 VIP")],
            [KeyboardButton(text="📢 Reklama va homiylik")]
        ],
        resize_keyboard=True
    )
    await message.answer("Asosiy menyu:", reply_markup=keyboard)

@router.callback_query(F.data == "search_by_code")
async def search_by_code_start(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_code)
    await callback.message.edit_text(
        "🔢 Anime kodini kiriting:\n"
        "Masalan: NAR001"
    )

@router.message(StateFilter(UserStates.waiting_for_code))
async def process_code_search(message: types.Message, state: FSMContext):
    async with async_session() as session:
        result = await session.execute(
            select(Anime).where(Anime.code == message.text)
        )
        anime = result.scalar_one_or_none()
        
        if not anime:
            await message.answer(
                "❌ Bunday kodli anime mavjud emas!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")
                    ]]
                )
            )
        else:
            # Epizodlar sonini olish
            episodes = await session.execute(
                select(Episode).where(Episode.anime_id == anime.id).order_by(Episode.episode_number)
            )
            episodes = episodes.scalars().all()
            
            # Epizod tugmalarini yaratish
            keyboard = []
            row = []
            for episode in episodes:
                row.append(
                    InlineKeyboardButton(
                        text=f"📺 {episode.episode_number}-qism",
                        callback_data=f"watch_{anime.code}_{episode.episode_number}"
                    )
                )
                if len(row) == 2:  # 2 tadan qilib joylashtirish
                    keyboard.append(row)
                    row = []
            
            if row:  # Qolgan tugmalarni qo'shish
                keyboard.append(row)
            
            # Qo'shimcha tugmalar
            keyboard.append([
                InlineKeyboardButton(text="⬇️ Hammasini yuklash", callback_data=f"download_all_{anime.code}")
            ])
            keyboard.append([
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")
            ])
            
            # Anime ma'lumotlarini yuborish
            await message.answer_photo(
                photo=anime.image_url,
                caption=(
                    f"📺 <b>{anime.title}</b>\n\n"
                    f"📝 <i>{anime.description}</i>\n\n"
                    f"🎭 Janr: {anime.genre}\n"
                    f"🌍 Davlat: {anime.country}\n"
                    f"🗣 Til: {anime.language}\n"
                    f"🔢 Kod: <code>{anime.code}</code>\n"
                    f"👁 Ko'rilgan: {anime.views:,} marta\n\n"
                    f"📺 Mavjud qismlar soni: {len(episodes)} ta"
                ),
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                parse_mode="HTML"
            )
            
            # Ko'rishlar sonini oshirish
            anime.views += 1
            await session.commit()
    
    await state.clear()

@router.callback_query(lambda c: c.data.startswith('anime_'))
async def show_anime_details(callback: types.CallbackQuery):
    anime_code = callback.data.split('_')[1]
    
    async with async_session() as session:
        # Animeni topish
        result = await session.execute(
            select(Anime).where(Anime.code == anime_code)
        )
        anime = result.scalar_one_or_none()
        
        if not anime:
            await callback.answer("❌ Anime topilmadi!")
            return
        
        # Epizodlarni olish
        result = await session.execute(
            select(Episode).where(Episode.anime_id == anime.id).order_by(Episode.episode_number)
        )
        episodes = result.scalars().all()
        
        # Epizod tugmalarini yaratish
        keyboard = []
        row = []
        for episode in episodes:
            row.append(
                InlineKeyboardButton(
                    text=f"📺 {episode.episode_number}-qism",
                    callback_data=f"watch_{anime.code}_{episode.episode_number}"
                )
            )
            if len(row) == 2:  # 2 tadan qilib joylashtirish
                keyboard.append(row)
                row = []
        
        if row:  # Qolgan tugmalarni qo'shish
            keyboard.append(row)
        
        # Qo'shimcha tugmalar
        keyboard.append([
            InlineKeyboardButton(text="⬇️ Hammasini yuklash", callback_data=f"download_all_{anime.code}")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")
        ])
        
        # Anime ma'lumotlarini yuborish
        await callback.message.delete()  # Eski xabarni o'chirish
        await callback.message.answer_photo(
            photo=anime.image_url,
            caption=(
                f"📺 <b>{anime.title}</b>\n\n"
                f"📝 <i>{anime.description}</i>\n\n"
                f"🎭 Janr: {anime.genre}\n"
                f"🌍 Davlat: {anime.country}\n"
                f"🗣 Til: {anime.language}\n"
                f"🔢 Kod: <code>{anime.code}</code>\n"
                f"👁 Ko'rilgan: {anime.views:,} marta\n\n"
                f"📺 Mavjud qismlar soni: {len(episodes)} ta"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
        
        # Ko'rishlar sonini oshirish
        anime.views += 1
        await session.commit()

@router.callback_query(lambda c: c.data.startswith('watch_'))
async def watch_episode(callback: types.CallbackQuery):
    _, anime_code, episode_number = callback.data.split('_')
    
    async with async_session() as session:
        # Animeni topish
        result = await session.execute(
            select(Anime).where(Anime.code == anime_code)
        )
        anime = result.scalar_one_or_none()
        
        if not anime:
            await callback.answer("❌ Anime topilmadi!")
            return
        
        # Epizodni topish
        result = await session.execute(
            select(Episode).where(
                Episode.anime_id == anime.id,
                Episode.episode_number == int(episode_number)
            )
        )
        episode = result.scalar_one_or_none()
        
        if not episode:
            await callback.answer("❌ Qism topilmadi!")
            return
        
        # VIP tekshirish
        result = await session.execute(
            select(VIPUser).where(
                VIPUser.user_id == str(callback.from_user.id),
                VIPUser.is_vip == True
            )
        )
        vip_user = result.scalar_one_or_none()
        
        # Epizodlar sonini olish
        result = await session.execute(
            select(Episode).where(Episode.anime_id == anime.id)
        )
        total_episodes = len(result.scalars().all())
        
        # Agar oxirgi qism bo'lsa va VIP bo'lmasa
        if not vip_user and int(episode_number) == total_episodes:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="👑 VIP bo'lish", callback_data="vip")
                ]]
            )
            await callback.message.answer(
                "👑 Oxirgi qismni ko'rish uchun VIP bo'lishingiz kerak!",
                reply_markup=keyboard
            )
            return
        
        # Video yuborish
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"anime_{anime_code}")
            ]]
        )
        
        await callback.message.answer_video(
            video=episode.video_file_id,
            caption=(
                f"📺 {anime.title}\n"
                f"🎬 {episode.episode_number}-qism"
            ),
            reply_markup=keyboard
        )
        
        # Ko'rishlar sonini oshirish
        episode.views += 1
        await session.commit()

async def vip_menu(message: types.Message):
    async with async_session() as session:
        admin = session.query(Admin).first()
        
        if not admin or not admin.card_number:
            await message.answer("❌ VIP to'lov tizimi hozircha ishlamayapti. Keyinroq urinib ko'ring.")
            return
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="✨ VIP afzalliklari", callback_data="vip_info")]
            ]
        )
        
        await message.answer(
            f"👑 VIP obuna narxi: {admin.vip_price:,} so'm\n\n"
            f"💳 To'lov uchun karta:\n"
            f"`{admin.card_number}`\n\n"
            f"📝 To'lov qilish tartibi:\n"
            f"1. Yuqoridagi kartaga to'lov qiling\n"
            f"2. To'lov chekini @admin_username ga yuboring\n"
            f"3. Admin tekshirib VIP statusini beradi\n\n"
            f"❓ VIP afzalliklarini ko'rish uchun pastdagi tugmani bosing",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

async def contact_admin(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👨‍💻 Admin bilan bog'lanish", url="https://t.me/your_username")]
        ]
    )
    await message.answer(
        "📞 Admin bilan bog'lanish:\n\n"
        "💰 Reklama berish\n"
        "🤝 Hamkorlik qilish\n"
        "❓ Savollar bo'yicha\n\n"
        "👉 Pastdagi tugmani bosing",
        reply_markup=keyboard
    )

async def show_most_viewed(message: types.Message):
    # VIP ekanligini tekshirish
    async with async_session() as session:
        vip_user = session.query(VIPUser).filter_by(user_id=str(message.from_user.id), is_vip=True).first()
        admin = session.query(Admin).first()
        
        if not vip_user or vip_user.expire_date < datetime.now():
            # VIP bo'lmasa yoki muddati tugagan bo'lsa
            vip_price = admin.vip_price if admin else 50000  # Standart narx
            
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="💳 VIP sotib olish", callback_data="pay_vip")],
                    [InlineKeyboardButton(text="✨ VIP afzalliklari", callback_data="vip_info")]
                ]
            )
            
            await message.answer(
                f"⭐️ Eng ko'p ko'rilgan animalarni ko'rish uchun VIP bo'lishingiz kerak!\n\n"
                f"💰 VIP narxi: {vip_price:,} so'm\n\n"
                f"✨ VIP afzalliklari:\n"
                f"• Eng ko'p ko'rilgan animalarni ko'rish\n"
                f"• Yangi qismlardan birinchi xabardor bo'lish\n"
                f"• Reklamasiz ko'rish\n"
                f"• Premium kontent\n\n"
                f"💳 To'lov uchun karta:\n"
                f"`{admin.card_number}`\n\n"
                f"📝 To'lov qilish tartibi:\n"
                f"1. Yuqoridagi kartaga to'lov qiling\n"
                f"2. To'lov chekini @admin_username ga yuboring\n"
                f"3. Admin tekshirib VIP statusini beradi",
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            return
        
        # VIP foydalanuvchi uchun eng ko'p ko'rilgan animalarni ko'rsatish
        top_animes = session.query(Anime).order_by(Anime.views.desc()).limit(10).all()
        
        if not top_animes:
            await message.answer("❌ Hozircha animalar mavjud emas.")
            return
        
        result = "🏆 Eng ko'p ko'rilgan TOP-10 animalar:\n\n"
        
        for i, anime in enumerate(top_animes, 1):
            # Anime qismlarini olish
            episodes = session.query(Episode).filter_by(anime_id=anime.id).count()
            
            result += (
                f"{i}. {anime.title}\n"
                f"   └ Ko'rildi: {anime.views:,} marta\n"
                f"   └ Kod: {anime.code}\n"
                f"   └ Janr: {anime.genre}\n"
                f"   └ Qismlar soni: {episodes} ta\n\n"
            )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_top")]
            ]
        )
        
        await message.answer(result, reply_markup=keyboard)

async def vip_callback_handler(callback: types.CallbackQuery):
    if callback.data == "pay_vip":
        async with async_session() as session:
            admin = session.query(Admin).first()
            
            if admin and admin.card_number:
                await callback.message.answer(
                    f"💳 To'lov uchun karta raqami:\n"
                    f"`{admin.card_number}`\n\n"
                    f"To'lov qilgach, to'lov chekini @admin_username ga yuboring.",
                    parse_mode="Markdown"
                )
            else:
                await callback.message.answer("❌ To'lov tizimi vaqtinchalik ishlamayapti. Keyinroq urinib ko'ring.")
    
    elif callback.data == "vip_info":
        await callback.message.answer(
            "✨ VIP AFZALLIKLARI:\n\n"
            "1. Eng ko'p ko'rilgan animalarni ko'rish\n"
            "2. Yangi qismlardan birinchi xabardor bo'lish\n"
            "3. Reklamasiz ko'rish\n"
            "4. Premium kontent\n"
            "5. Yuqori tezlikda yuklab olish\n\n"
            "VIP muddat: 30 kun"
        )
    
    await callback.answer()

async def download_all_episodes(callback: types.CallbackQuery):
    _, _, anime_code = callback.data.split("_")
    
    async with async_session() as session:
        anime = session.query(Anime).filter_by(code=anime_code).first()
        episodes = session.query(Episode).filter_by(anime_id=anime.id).order_by(Episode.episode_number).all()
        
        if not episodes:
            await callback.answer("❌ Qismlar topilmadi!")
            return
        
        await callback.message.answer(f"📥 {anime.title} - barcha qismlar yuklanmoqda...")
        
        for episode in episodes:
            await callback.message.answer_video(
                video=episode.video_file_id,
                caption=f"📥 {anime.title} - {episode.episode_number}-qism"
            )
        
        await callback.answer()

async def download_episode(callback: types.CallbackQuery):
    _, anime_code, episode_number = callback.data.split("_")
    
    async with async_session() as session:
        anime = session.query(Anime).filter_by(code=anime_code).first()
        episode = session.query(Episode).filter_by(
            anime_id=anime.id, 
            episode_number=int(episode_number)
        ).first()
        
        if not episode:
            await callback.answer("❌ Qism topilmadi!")
            return
        
        # Video yuborish
        await callback.message.answer_video(
            video=episode.video_file_id,
            caption=f"📥 {anime.title} - {episode_number}-qism\n\n"
                    f"✅ Yuklab olish uchun videoni bosing"
        )
        
        await callback.answer()

async def download_anime_videos(callback: types.CallbackQuery):
    _, _, anime_code = callback.data.split("_")
    
    async with async_session() as session:
        anime = session.query(Anime).filter_by(code=anime_code).first()
        episodes = session.query(Episode).filter_by(anime_id=anime.id).order_by(Episode.episode_number).all()
        
        if not episodes:
            await callback.message.answer("❌ Bu anime uchun hali videolar qo'shilmagan!")
            await callback.answer()
            return
        
        await callback.message.answer(f"📥 {anime.title} - barcha qismlar yuklanmoqda...")
        
        for episode in episodes:
            # Video yuborish
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📥 Yuklab olish", callback_data=f"download_{anime.code}_{episode.episode_number}")]
                ]
            )
            
            await callback.message.answer_video(
                video=episode.video_file_id,
                caption=f"🎬 {anime.title}\n"
                        f"📺 {episode.episode_number}-qism",
                reply_markup=keyboard
            )
        
        await callback.answer()

async def vip_info_callback(callback: types.CallbackQuery):
    await callback.message.answer(
        "✨ VIP AFZALLIKLARI:\n\n"
        "1. Eng ko'p ko'rilgan animalarni ko'rish\n"
        "2. Yangi qismlardan birinchi xabardor bo'lish\n"
        "3. Reklamasiz ko'rish\n"
        "4. Premium kontent\n"
        "5. Yuqori tezlikda yuklab olish\n\n"
        "VIP muddat: 30 kun"
    )
    await callback.answer()

async def refresh_top_animes(callback: types.CallbackQuery):
    # VIP tekshirish
    async with async_session() as session:
        vip_user = session.query(VIPUser).filter_by(user_id=str(callback.from_user.id), is_vip=True).first()
        
        if not vip_user or vip_user.expire_date < datetime.now():
            await callback.answer("❌ VIP obuna muddati tugagan!")
            return
        
        # Yangilangan TOP-10
        top_animes = session.query(Anime).order_by(Anime.views.desc()).limit(10).all()
        
        if not top_animes:
            await callback.answer("❌ Hozircha animalar mavjud emas.")
            return
        
        result = "🏆 Eng ko'p ko'rilgan TOP-10 animalar:\n\n"
        
        for i, anime in enumerate(top_animes, 1):
            episodes = session.query(Episode).filter_by(anime_id=anime.id).count()
            
            result += (
                f"{i}. {anime.title}\n"
                f"   └ Ko'rildi: {anime.views:,} marta\n"
                f"   └ Kod: {anime.code}\n"
                f"   └ Janr: {anime.genre}\n"
                f"   └ Qismlar soni: {episodes} ta\n\n"
            )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_top")]
            ]
        )
        
        await callback.message.edit_text(result, reply_markup=keyboard)
        await callback.answer("✅ Ma'lumotlar yangilandi!")

@router.message(F.text == "panel")
async def admin_panel(message: types.Message):
    # Adminligini tekshirish
    if str(message.from_user.id) in os.getenv("ADMINS", "").split(","):
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="➕ Anime qo'shish", callback_data="add_anime"),
                    InlineKeyboardButton(text="➕ Qism qo'shish", callback_data="add_episode")
                ],
                [
                    InlineKeyboardButton(text="💰 VIP narxi", callback_data="change_vip_price"),
                    InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")
                ],
                [
                    InlineKeyboardButton(text="🗑 Anime o'chirish", callback_data="delete_anime"),
                    InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_anime")
                ]
            ]
        )
        
        await message.answer(
            "👨‍💻 Admin panel\n\n"
            "Quyidagi amallardan birini tanlang:",
            reply_markup=keyboard
        )
    else:
        await message.answer("❌ Sizda admin huquqlari yo'q!")

@router.callback_query(F.data == "show_stats")
async def show_statistics(callback: types.CallbackQuery):
    async with async_session() as session:
        # Statistika ma'lumotlarini olish
        result = await session.execute(select(Anime))
        total_animes = len(result.scalars().all())
        
        result = await session.execute(select(Episode))
        total_episodes = len(result.scalars().all())
        
        result = await session.execute(select(VIPUser).where(VIPUser.is_vip == True))
        total_vip_users = len(result.scalars().all())
        
        text = (
            "📊 BOT STATISTIKASI\n\n"
            f"📺 Jami animalar: {total_animes} ta\n"
            f"🎬 Jami qismlar: {total_episodes} ta\n"
            f"👑 VIP foydalanuvchilar: {total_vip_users} ta\n"
        )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_stats")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_admin")]
            ]
        )
        
        await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_panel(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Anime qo'shish", callback_data="add_anime"),
                InlineKeyboardButton(text="➕ Qism qo'shish", callback_data="add_episode")
            ],
            [
                InlineKeyboardButton(text="💰 VIP narxi", callback_data="change_vip_price"),
                InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")
            ],
            [
                InlineKeyboardButton(text="🗑 Anime o'chirish", callback_data="delete_anime"),
                InlineKeyboardButton(text="✏️ Tahrirlash", callback_data="edit_anime")
            ]
        ]
    )
    
    await callback.message.edit_text(
        "👨‍💻 Admin panel\n\n"
        "Quyidagi amallardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "search_by_genre")
async def search_by_genre_start(callback: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎭 Action", callback_data="genre_Action"),
                InlineKeyboardButton(text="🌟 Adventure", callback_data="genre_Adventure")
            ],
            [
                InlineKeyboardButton(text="💕 Romance", callback_data="genre_Romance"),
                InlineKeyboardButton(text="🎪 Comedy", callback_data="genre_Comedy")
            ],
            [
                InlineKeyboardButton(text="🔮 Fantasy", callback_data="genre_Fantasy"),
                InlineKeyboardButton(text="🎭 Drama", callback_data="genre_Drama")
            ],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="search")]
        ]
    )
    
    await callback.message.edit_text(
        "🎭 Qidirilayotgan janrni tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith('genre_'))
async def show_genre_animes(callback: types.CallbackQuery):
    genre = callback.data.split('_')[1]
    
    async with async_session() as session:
        result = await session.execute(
            select(Anime).where(Anime.genre.ilike(f"%{genre}%"))
        )
        animes = result.scalars().all()
        
        if not animes:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="🔙 Orqaga", callback_data="search_by_genre")
                ]]
            )
            await callback.message.edit_text(
                f"❌ {genre} janridagi animalar topilmadi!",
                reply_markup=keyboard
            )
            return
        
        text = f"🎭 {genre} janridagi animalar:\n\n"
        keyboard = []
        
        for anime in animes:
            text += f"📺 {anime.title}\n"
            text += f"🔢 Kod: {anime.code}\n"
            text += f"👁 Ko'rilgan: {anime.views:,} marta\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{anime.title}", 
                    callback_data=f"anime_{anime.code}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="search_by_genre")
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@router.callback_query(F.data == "show_all_animes")
async def show_all_animes(callback: types.CallbackQuery):
    async with async_session() as session:
        result = await session.execute(
            select(Anime).order_by(Anime.title)
        )
        animes = result.scalars().all()
        
        if not animes:
            await callback.message.edit_text(
                "❌ Hozircha animalar mavjud emas!",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="🔙 Orqaga", callback_data="search")
                    ]]
                )
            )
            return
        
        text = "📺 BARCHA ANIMALAR:\n\n"
        keyboard = []
        
        for anime in animes:
            # Epizodlar sonini olish
            episodes_result = await session.execute(
                select(Episode).where(Episode.anime_id == anime.id)
            )
            episodes_count = len(episodes_result.scalars().all())
            
            text += f"🎬 {anime.title}\n"
            text += f"🎭 Janr: {anime.genre}\n"
            text += f"🔢 Kod: {anime.code}\n"
            text += f"📺 Qismlar: {episodes_count} ta\n"
            text += f"👁 Ko'rilgan: {anime.views:,} marta\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{anime.title}", 
                    callback_data=f"anime_{anime.code}"
                )
            ])
        
        # Sahifalash tugmalari
        keyboard.append([
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="search")
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

@router.callback_query(F.data == "ads_sponsor")
async def show_ads_sponsor_menu(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📢 Reklama berish", callback_data="place_ad"),
                InlineKeyboardButton(text="🤝 Homiylik", callback_data="become_sponsor")
            ],
            [
                InlineKeyboardButton(text="💰 Narxlar", callback_data="show_prices"),
                InlineKeyboardButton(text="📞 Admin bilan bog'lanish", callback_data="contact_admin")
            ],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_menu")]
        ]
    )
    
    await callback.message.edit_text(
        "📢 REKLAMA VA HOMIYLIK\n\n"
        "Bot orqali reklama berish yoki homiy bo'lish uchun quyidagi bo'limlardan birini tanlang:",
        reply_markup=keyboard
    )

@router.callback_query(F.data == "place_ad")
async def show_ad_prices(callback: types.CallbackQuery):
    text = (
        "📢 REKLAMA NARXLARI\n\n"
        "1️⃣ Oddiy e'lon (24 soat):\n"
        "• Barcha foydalanuvchilarga yuboriladi\n"
        "• Narxi: 50,000 so'm\n\n"
        "2️⃣ Premium e'lon (3 kun):\n"
        "• Barcha foydalanuvchilarga yuboriladi\n"
        "• Bot kanalida qoladi\n"
        "• Narxi: 100,000 so'm\n\n"
        "3️⃣ VIP e'lon (7 kun):\n"
        "• Barcha foydalanuvchilarga yuboriladi\n"
        "• Bot kanalida qoladi\n"
        "• Har kuni qayta yuboriladi\n"
        "• Narxi: 200,000 so'm\n\n"
        "✅ Reklama berish uchun admin bilan bog'laning"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📞 Admin bilan bog'lanish", url="https://t.me/admin_username")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="ads_sponsor")
            ]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "become_sponsor")
async def show_sponsor_info(callback: types.CallbackQuery):
    text = (
        "🤝 HOMIYLIK SHARTLARI\n\n"
        "Bot homiysi bo'lish orqali quyidagi imkoniyatlarga ega bo'lasiz:\n\n"
        "1️⃣ SILVER HOMIY (500,000 so'm/oy):\n"
        "• Botda logotip joylashtirish\n"
        "• Har hafta 1 ta reklama\n"
        "• VIP status\n\n"
        "2️⃣ GOLD HOMIY (1,000,000 so'm/oy):\n"
        "• Botda logotip joylashtirish\n"
        "• Har kuni 1 ta reklama\n"
        "• VIP status\n"
        "• Maxsus chegirmalar\n\n"
        "3️⃣ PLATINUM HOMIY (2,000,000 so'm/oy):\n"
        "• Botda logotip joylashtirish\n"
        "• Cheksiz reklama\n"
        "• VIP status\n"
        "• Maxsus chegirmalar\n"
        "• Botda brend nomi\n\n"
        "✅ Homiy bo'lish uchun admin bilan bog'laning"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📞 Admin bilan bog'lanish", url="https://t.me/admin_username")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="ads_sponsor")
            ]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "show_prices")
async def show_all_prices(callback: types.CallbackQuery):
    text = (
        "💰 NARXLAR RO'YXATI\n\n"
        "📢 REKLAMA:\n"
        "• Oddiy e'lon: 50,000 so'm\n"
        "• Premium e'lon: 100,000 so'm\n"
        "• VIP e'lon: 200,000 so'm\n\n"
        "🤝 HOMIYLIK:\n"
        "• Silver: 500,000 so'm/oy\n"
        "• Gold: 1,000,000 so'm/oy\n"
        "• Platinum: 2,000,000 so'm/oy\n\n"
        "👑 VIP OBUNA:\n"
        "• 1 oylik: 50,000 so'm\n"
        "• 3 oylik: 120,000 so'm\n"
        "• 6 oylik: 200,000 so'm\n\n"
        "💳 To'lov usullari:\n"
        "• Click\n"
        "• Payme\n"
        "• Bank karta\n\n"
        "✅ Batafsil ma'lumot uchun admin bilan bog'laning"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📞 Admin bilan bog'lanish", url="https://t.me/admin_username")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="ads_sponsor")
            ]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "contact_admin")
async def show_contact_admin(callback: types.CallbackQuery):
    text = (
        "📞 ADMIN BILAN BOG'LANISH\n\n"
        "Admin bilan quyidagi mavzularda bog'lanishingiz mumkin:\n\n"
        "📢 Reklama berish\n"
        "🤝 Homiylik qilish\n"
        "💰 To'lovlar\n"
        "❓ Savollar va takliflar\n\n"
        "⏰ Ish vaqti: 9:00 - 18:00\n\n"
        "✅ Bog'lanish uchun quyidagi tugmani bosing"
    )
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👨‍💻 Admin", url="https://t.me/admin_username")
            ],
            [
                InlineKeyboardButton(text="🔙 Orqaga", callback_data="ads_sponsor")
            ]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard)

async def check_subscription(user_id: int) -> bool:
    """Foydalanuvchi kanallarga obuna bo'lganligini tekshirish"""
    # Admin tekshirish
    if str(user_id) in os.getenv("ADMINS", "").split(","):
        return True
        
    async with async_session() as session:
        # Barcha kanallarni olish
        result = await session.execute(select(Channel))
        channels = result.scalars().all()
        
        for channel in channels:
            try:
                member = await bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
                if member.status in ['left', 'kicked', 'banned']:
                    return False
            except Exception:
                continue
        return True

async def get_channels_keyboard() -> InlineKeyboardMarkup:
    """Obuna bo'lish uchun kanallar ro'yxatini qaytaradi"""
    async with async_session() as session:
        result = await session.execute(select(Channel))
        channels = result.scalars().all()
        
        keyboard = []
        for channel in channels:
            keyboard.append([
                InlineKeyboardButton(text=f"➕ {channel.channel_name}", url=f"https://t.me/{channel.channel_url[1:]}")
            ])
        
        keyboard.append([
            InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription")
        ])
        
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.callback_query(F.data == "check_subscription")
async def check_subscription_handler(callback: types.CallbackQuery):
    if await check_subscription(callback.from_user.id):
        await callback.message.delete()
        await start_command(callback.message)
    else:
        await callback.answer("❌ Siz hali barcha kanallarga obuna bo'lmagansiz!", show_alert=True) 