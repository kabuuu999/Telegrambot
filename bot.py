import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import bd  # импортируем модуль работы с базой

import os
TOKEN = os.getenv("TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=["start"])
async def cmd_start(message: types.Message):
    await bd.add_user(message.from_user)
    await message.answer("Привет! Я бот с системой браков. Чтобы узнать команды, напиши /help.")

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    text = (
        "Команды бота:\n"
        "/marry @username — предложить брак\n"
        "/divorce @username — развестись\n"
        "/spouses — показать список супругов\n"
    )
    await message.answer(text)

@dp.message_handler(commands=["marry"])
async def cmd_marry(message: types.Message):
    await bd.add_user(message.from_user)
    if not message.reply_to_message and not message.get_args():
        await message.answer("Чтобы предложить брак, ответь на сообщение пользователя или напиши /marry @username")
        return

    target_user = None

    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        args = message.get_args().strip()
        if args.startswith("@"):
            username = args[1:]
            # Ищем пользователя в базе
            async with bd.aiosqlite.connect(bd.DB_PATH) as db:
                async with db.execute(
                    "SELECT user_id FROM users WHERE username = ?", (username,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        target_user = types.User(id=row[0], is_bot=False, first_name=username)
                    else:
                        await message.answer("Пользователь не найден или ещё не взаимодействовал с ботом.")
                        return
        else:
            await message.answer("Некорректный формат. Используй /marry @username")
            return

    if target_user.id == message.from_user.id:
        await message.answer("Ты не можешь вступить в брак с самим собой!")
        return

    if await bd.are_married(message.from_user.id, target_user.id):
        await message.answer(f"Вы уже в браке с @{target_user.username or 'пользователем'}.")
        return

    proposal_keyboard = InlineKeyboardMarkup(row_width=2)
    proposal_keyboard.add(
        InlineKeyboardButton("Принять", callback_data=f"accept_{message.from_user.id}"),
        InlineKeyboardButton("Отклонить", callback_data=f"reject_{message.from_user.id}"),
    )
    await bot.send_message(target_user.id, f"@{message.from_user.username} предложил(а) тебе брак! Принять?", reply_markup=proposal_keyboard)
    await message.answer(f"Предложение брака отправлено @{target_user.username or 'пользователю'}.")

@dp.callback_query_handler(lambda c: c.data and (c.data.startswith("accept_") or c.data.startswith("reject_")))
async def process_callback(callback_query: types.CallbackQuery):
    data = callback_query.data
    action, proposer_id_str = data.split("_")
    proposer_id = int(proposer_id_str)
    responder_id = callback_query.from_user.id

    if action == "accept":
        if await bd.are_married(proposer_id, responder_id):
            await callback_query.answer("Вы уже в браке.")
            return
        await bd.create_marriage(proposer_id, responder_id)
        await callback_query.answer("Брак оформлен! Поздравляю! ❤️")
        await bot.send_message(proposer_id, f"@{callback_query.from_user.username} принял(а) предложение брака! 🎉")
        await bot.send_message(responder_id, f"Вы теперь в браке с @{(await bot.get_chat(proposer_id)).username}!")
    elif action == "reject":
        await callback_query.answer("Предложение отклонено.")
        await bot.send_message(proposer_id, f"@{callback_query.from_user.username} отклонил(а) ваше предложение брака.")
    await callback_query.message.delete()

@dp.message_handler(commands=["divorce"])
async def cmd_divorce(message: types.Message):
    if not message.reply_to_message and not message.get_args():
        await message.answer("Чтобы развестись, ответь на сообщение супруга или напиши /divorce @username")
        return

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        args = message.get_args().strip()
        if args.startswith("@"):
            username = args[1:]
            async with bd.aiosqlite.connect(bd.DB_PATH) as db:
                async with db.execute(
                    "SELECT user_id FROM users WHERE username = ?", (username,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        target_user = types.User(id=row[0], is_bot=False, first_name=username)
                    else:
                        await message.answer("Пользователь не найден или ещё не взаимодействовал с ботом.")
                        return
        else:
            await message.answer("Некорректный формат. Используй /divorce @username")
            return

    if not await bd.are_married(message.from_user.id, target_user.id):
        await message.answer("Вы не в браке с этим пользователем.")
        return

    await bd.delete_marriage(message.from_user.id, target_user.id)
    await message.answer(f"Вы развелись с @{target_user.username or 'пользователем'}.")

@dp.message_handler(commands=["spouses"])
async def cmd_spouses(message: types.Message):
    spouses_ids = await bd.get_spouses(message.from_user.id)
    if not spouses_ids:
        await message.answer("У вас нет супругов.")
        return
    text = "Ваши супруги:\n"
    for uid in spouses_ids:
        try:
            user = await bot.get_chat(uid)
            text += f"@{user.username or user.first_name}\n"
        except:
            text += f"Пользователь {uid}\n"
    await message.answer(text)

if __name__ == "__main__":
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bd.init_db())
    executor.start_polling(dp, skip_updates=True)
