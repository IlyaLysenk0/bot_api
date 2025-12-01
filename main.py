# Бот дает курс валют, дает график за последнюю неделю/месяц, дает изменение за посленюю неделю/месяц
# Интеграция функционала фиктивной сделки с докупом/фиксацией/автопродажей
#Сохранение сделок, статистика по сделаным сделкам, история сделок
import os
from aiohttp import web
import logging
import aiohttp
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot_db import Session, Active_users, Price, init_db

TOKEN = "8421330855:AAElG01w1GDHVbXDlmOo30tlLBOgyovk_Kc"
admin_chat_id = 1002506955

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

scheduler = AsyncIOScheduler()


# --------------------------------------------------------------------------------------------------------


async def health_check(request):
    return web.Response(text="Bot is alive!")


async def start_web_server():
    app = web.Application()
    app.router.add_get('/', health_check)
    runner = web.AppRunner(app)
    await runner.setup()

    # Render видає порт через змінну оточення PORT. Якщо її немає - беремо 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"Web server started on port {port}")



# --------------------------------------------------------------------------

all_prodlems = []

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Курс")],
    ],
    resize_keyboard=True,       # підлаштовує розмір під екран
    input_field_placeholder="Выбрать опцию"  # підказка
)


async def api_info(str_format=False):
    try:
        url_list = ['https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT','https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT','https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT']
        info_dict = {}
        async with aiohttp.ClientSession() as session:
            for url in url_list:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        info_dict[str(data['symbol'])[:3]] = float(data['price'])
                    else:
                        return False
        if str_format:
            result_str = ''
            for name, price in info_dict.items():
                result_str += f"{name}  ---->  {price} $\n"
            return result_str

        return info_dict
    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(str(e))


def add_to_bd(api:dict):
    try:
        with Session() as ss:
            for name, price in api.items():
                new_add = Price(name=name, price=price)
                ss.add(new_add)
            ss.commit()
    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(str(e))

async def get_info(chat_id: int, in_to_db=False):
    try:
        api_result_str = ''
        api_result = await api_info()
        for name, price in api_result.items():
            api_result_str += f"{name}  ---->  {price} $\n"
        await bot.send_message(chat_id, api_result_str)
        if chat_id == admin_chat_id and in_to_db:
            add_to_bd(api_result)

    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(f"Не вдалося надіслати повідомлення користувачу {chat_id}: {e}")


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    try:
        user_tg_id = message.from_user.id
        with Session() as ss:
            user = ss.query(Active_users).filter_by(tg_id = user_tg_id).first()
            if not user:
                new_user = Active_users(tg_id = user_tg_id, unique_name=message.from_user.username, tg_name=message.from_user.first_name,user_language=message.from_user.language_code)
                ss.add(new_user)
                ss.commit()
        await message.answer("""Готово!\nБот отправляет курс каждые 4 часа после последней отправки курса. Проверить курс "в моменте" можно по кнопке "Курс" или по команде /check""",reply_markup=main_menu)
    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(str(e))

@dp.message(Command("check"))
@dp.message(F.text.lower()=='курс')
async def check(message: types.Message):
    try:
        user_tg_id = message.from_user.id
        with Session() as ss:
            user = ss.query(Active_users).filter_by(tg_id=user_tg_id).first()
            if not user:
                new_user = Active_users(tg_id=user_tg_id, unique_name=message.from_user.username,tg_name=message.from_user.first_name, user_language=message.from_user.language_code)
                ss.add(new_user)
                ss.commit()
            else:
                user.requests_counter += 1
                ss.commit()

        if scheduler.get_job(str(user_tg_id)):
            scheduler.remove_job(str(user_tg_id))
        #     hours
        scheduler.add_job(get_info, 'interval',hours=1,args=[user_tg_id,True],id=str(user_tg_id))
        api_result = await api_info(str_format=True)
        await message.answer(api_result)
    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(str(e))

@dp.message(Command("check_free"))
async def check_free(message: types.Message):
    try:
        api_result = await api_info(str_format=True)
        await message.answer(api_result)
    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(str(e))

@dp.message(Command("save_problems"))
async def save_problems(message: types.Message):
    try:
        user_tg_id = message.from_user.id
        if user_tg_id == admin_chat_id:
            if all_prodlems:
                with open('problem.txt','a', encoding='utf-8') as f:
                    for i in all_prodlems:
                        f.write(i+'\n\n\n\n\n\n\n\n')
                all_prodlems.clear()
                await message.answer('Помилки записані')
            else:
                await message.answer('Помилок немає')
    except Exception as e:
        logging.error(f"Сталася помилка: {e}", exc_info=True)
        all_prodlems.append(str(e))

















# async def main():
#     init_db()
#     scheduler.start()
#     await bot.delete_webhook(drop_pending_updates=True)
#     await dp.start_polling(bot)

async def main():
    init_db() # Якщо використовуєш
    scheduler.start()

    # Запускаємо веб-сервер, щоб Render бачив активність
    await start_web_server()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
