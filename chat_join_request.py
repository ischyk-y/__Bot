from aiogram import Router
from aiogram.types import ChatJoinRequest, ChatMemberUpdated, ChatMemberLeft
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER

from database.database import Database
from database.redis_database import RedisDatabase

from helpers.helpers import get_invite_link

router = Router()  # [1]

db = Database()
redis_db = RedisDatabase()


async def get_chat_id(tg_id: int) -> int:
    chat_id = redis_db.get(f'chat:{tg_id}')

    if not chat_id:
        query = '''
            SELECT id FROM chats WHERE tg_id = $1;
        '''
        chat_id = await db.query('fetchval', query, tg_id)

        if chat_id:
            redis_db.set(f'chat:{tg_id}', chat_id)

    return int(chat_id) if chat_id else None


async def set_chat(tg_id: int, title: str) -> int:
    query = '''
        INSERT INTO chats (bot_id, tg_id, title)
        VALUES (1, $1, $2)
        RETURNING id;
    '''
    chat_id = await db.query('fetchval', query, tg_id, title)

    redis_db.set(f'chat:{tg_id}', chat_id)

    return chat_id


async def get_c_invite_link(invite_link: str) -> list:
    c_invite_link = redis_db.hmget(f'c_invite_link:{invite_link}', 'id', 'chat_id')

    if c_invite_link[0]:
        return [int(i) for i in c_invite_link]
    else:
        query = 'SELECT id, chat_id FROM c_invite_links WHERE invite_link = $1'
        c_invite_link = await db.query('fetchrow', query, invite_link)

        if c_invite_link:
            redis_db.hset(f'c_invite_link:{invite_link}', mapping={
                'id': c_invite_link['id'],
                'chat_id': c_invite_link['chat_id']
            })
        return [c_invite_link['id'], c_invite_link['chat_id']] \
            if c_invite_link else None


async def set_c_invite_link(
        chat_id: int, invite_link: str, creates_join_request: bool, name) -> int:
    query = '''
        INSERT INTO c_invite_links
        (chat_id, invite_link, creates_join_request, name, date)
        VALUES ($1, $2, $3, $4, NOW())
        RETURNING id;
    '''
    c_invite_link_id = await db.query('fetchval', query,
                                      chat_id, invite_link, creates_join_request, name)

    redis_db.hset(f'c_invite_link:{invite_link}', mapping={
        'id': c_invite_link_id,
        'chat_id': chat_id
    })

    return c_invite_link_id


async def get_c_user_id(tg_id: int) -> int:
    user_id = redis_db.hget(f'user:{tg_id}', 'id')

    if not user_id:
        query = '''
            SELECT id FROM c_users WHERE tg_id = $1;
        '''
        user_id = await db.query('fetchval', query, tg_id)

    return int(user_id) if user_id else None


async def set_c_user(tg_id: int, first_name: str, last_name: str):
    query = '''
        INSERT INTO c_users (tg_id, first_name, last_name)
        VALUES ($1, $2, $3)
        RETURNING id;
    '''
    user_id = await db.query('fetchval', query, tg_id, first_name, last_name)

    return user_id


@router.chat_join_request()
@router.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def on_chat_join_request(event):
    if not event.invite_link:
        return

    date, invite_link, creates_join_request, name = \
        event.date, \
        get_invite_link(event.invite_link.invite_link), \
        event.invite_link.creates_join_request, \
        event.invite_link.name

    if isinstance(event, ChatMemberUpdated) and creates_join_request:
        return

    c_invite_link = await get_c_invite_link(invite_link)
    if not c_invite_link:
        chat_id = await get_chat_id(event.chat.id)
        if not chat_id:
            chat_id = await set_chat(event.chat.id, event.chat.title)
        c_invite_link_id = await set_c_invite_link(chat_id, invite_link, creates_join_request, name)
        c_invite_link = [c_invite_link_id, chat_id]

    chat_id = c_invite_link[1]
    c_invite_link_id = c_invite_link[0]

    if isinstance(event, ChatJoinRequest):
        tg_user_id = event.from_user.id
        first_name = event.from_user.first_name
        last_name = event.from_user.last_name
    else:
        tg_user_id = event.new_chat_member.user.id
        first_name = event.new_chat_member.user.first_name
        last_name = event.new_chat_member.user.last_name

    c_user_id = await get_c_user_id(tg_user_id)
    if not c_user_id:
        c_user_id = await set_c_user(tg_user_id, first_name, last_name)

    redis_db.hset(f'user:{tg_user_id}', mapping={
        'id': c_user_id,
        event.chat.id: c_invite_link_id
    })

    query = '''
        SELECT date FROM c_invite_links WHERE id = $1;
    '''
    date = await db.query('fetchval', query, c_invite_link_id)

    duration = (event.date - date).total_seconds()

    query = '''
        INSERT INTO c_requests (chat_id, c_invite_link_id, c_user_id, duration, status) 
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (chat_id, c_invite_link_id, c_user_id, status) DO NOTHING;
    '''
    await db.query('execute', query, chat_id, c_invite_link_id, c_user_id, int(duration), 'member')


@router.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def leave(event: ChatMemberLeft):
    tg_user_id = event.new_chat_member.user.id
    user = redis_db.hmget(f'user:{tg_user_id}', 'id', event.chat.id)

    if not user[0]:
        return

    chat_id = await get_chat_id(event.chat.id)

    if not chat_id:
        return

    c_user_id = int(user[0])
    c_invite_link_id = int(user[1])

    query = '''
        SELECT date FROM c_invite_links WHERE id = $1;
    '''
    date = await db.query('fetchval', query, c_invite_link_id)

    duration = (event.date - date).total_seconds()

    query = '''
        INSERT INTO c_requests (chat_id, c_invite_link_id, c_user_id, duration, status) 
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (chat_id, c_invite_link_id, c_user_id, status) DO NOTHING;
    '''
    await db.query('execute', query, chat_id, c_invite_link_id, c_user_id, int(duration), 'left')


