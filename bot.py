import asyncio
import logging
import os
import random
from typing import TypeVar

import aiofiles
import emoji
import ujson
from aiogram import Bot, Dispatcher
from aiogram.dispatcher.filters import ChatTypeFilter, Command, CommandStart, CommandHelp
from aiogram.types import AllowedUpdates, BotCommand, BotCommandScopeAllGroupChats, ChatType, Message, ParseMode

log = logging.getLogger(__name__)

JSON_TYPE = dict[str, list]
Element = TypeVar('Element')


def generate_pages(array: list[Element], elements_on_page: int) -> list[list[Element]]:
    length = len(array)
    pages_quantity = (length // elements_on_page)
    if length % elements_on_page != 0:
        pages_quantity += 1
    results = [array[page * elements_on_page: (page + 1) * elements_on_page] for page in range(pages_quantity)]
    return results


async def get_chat_users(chat_id: str) -> tuple[JSON_TYPE, set]:
    async with aiofiles.open('db.json') as file:
        contents = await file.read()
    json: JSON_TYPE = ujson.loads(contents)
    users = set(json.get(chat_id, []))
    return json, users


async def update_db(json: JSON_TYPE, chat_id: str, users: set):
    json.update({chat_id: list(users)})
    json = ujson.dumps(json, ensure_ascii=True, encode_html_chars=True, escape_forward_slashes=True, indent=2)
    async with aiofiles.open('db.json', 'w') as file:
        await file.write(json)


async def opt_out_user(chat_id: str, user_id: int) -> str:
    json, user_ids = await get_chat_users(chat_id)
    text = '{} нет в базе'
    if user_ids and user_id in user_ids:
        text = 'Пользователь {} успешно удалён из базы'
        user_ids.remove(user_id)
        await update_db(json, chat_id, user_ids)
    return text


async def opt_in_user(chat_id: str, user_id: int) -> str:
    json, user_ids = await get_chat_users(chat_id)
    text = '{} уже есть в базе'
    if user_id not in user_ids:
        text = 'Пользователь {} успешно добавлен в базу'
        user_ids.add(user_id)
        await update_db(json, chat_id, user_ids)
    return text


async def in_cmd(msg: Message):
    text = await opt_in_user(str(msg.chat.id), msg.from_user.id)
    await msg.reply(text.format(msg.from_user.get_mention()), disable_notification=True)


async def out_cmd(msg: Message):
    text = await opt_out_user(str(msg.chat.id), msg.from_user.id)
    await msg.reply(text.format(msg.from_user.get_mention()), disable_notification=True)


def get_mention(user_id: int) -> str:
    emj = random.choice(list(emoji.EMOJI_UNICODE_ENGLISH.values()))
    return f'[{emj}](tg://user?id={user_id})'


async def all_cmd(msg: Message):
    _, user_ids = await get_chat_users(str(msg.chat.id))
    if not user_ids:
        await msg.answer('Никого нет в базе, некого отмечать', disable_notification=True)
        return
    users = list(map(get_mention, user_ids))
    pages = generate_pages(list(users), 4)
    for page in pages:
        await msg.answer(' | '.join(page), disable_notification=False)
        await asyncio.sleep(0.3)
    await msg.answer('Успешно отмечены все пользователи', disable_notification=True)


async def start_cmd(msg: Message):
    text = [
        'Хай, я Бот для массовых отметок пользователей в групповых чатах Telegram',
        'Возможные команды можете посмотреть нажав на /',
        'Аккаунт разработчика: @corruptmane\n[Исходный код бота](https://github.com/corruptmane/notify-bot)'
    ]
    await msg.answer('\n\n'.join(text))


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(
        in_cmd, Command('in', '/', True, True, False), ChatTypeFilter((ChatType.GROUP, ChatType.SUPERGROUP))
    )
    dp.register_message_handler(
        in_cmd, Command('i', '/', True, True, False), ChatTypeFilter((ChatType.GROUP, ChatType.SUPERGROUP))
    )
    dp.register_message_handler(
        out_cmd, Command('out', '/', True, True, False), ChatTypeFilter((ChatType.GROUP, ChatType.SUPERGROUP))
    )
    dp.register_message_handler(
        out_cmd, Command('o', '/', True, True, False), ChatTypeFilter((ChatType.GROUP, ChatType.SUPERGROUP))
    )
    dp.register_message_handler(
        all_cmd, Command('all', '/', True, True, False), ChatTypeFilter((ChatType.GROUP, ChatType.SUPERGROUP))
    )
    dp.register_message_handler(
        all_cmd, Command('a', '/', True, True, False), ChatTypeFilter((ChatType.GROUP, ChatType.SUPERGROUP))
    )
    dp.register_message_handler(start_cmd, CommandStart())
    dp.register_message_handler(start_cmd, CommandHelp())


async def set_bot_commands(bot: Bot):
    start_command = BotCommand('start', 'Информация о боте')
    await bot.set_my_commands([
        BotCommand('in', 'Войти в базу'),
        BotCommand('out', 'Выйти из базы'),
        BotCommand('all', 'Отметить пользователей'),
        start_command,
        BotCommandScopeAllGroupChats()
    ])
    await bot.set_my_commands([start_command])


async def main():
    logging.basicConfig(
        level=logging.DEBUG,
        format=u'%(filename)s:%(lineno)d #%(levelname)-8s [%(asctime)s] - %(name)s - %(message)s',
    )
    log.info('Starting bot...')
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    bot = Bot(BOT_TOKEN, parse_mode=ParseMode.MARKDOWN_V2)
    dp = Dispatcher(bot)

    register_handlers(dp)
    await set_bot_commands(bot)
    allowed_updates = AllowedUpdates.MESSAGE

    try:
        await dp.start_polling(allowed_updates=allowed_updates)
    finally:
        session = await bot.get_session()
        await session.close()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.warning('Exiting...')
