import asyncio
from sqlalchemy import select
from app.database.base import async_session
from app.database.models import User

async def main():
    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Всего пользователей в БД: {len(users)}")
        for u in users:
            print(f"  id={u.id} | tg={u.telegram_id} | name={u.first_name} | role={u.role}")

if __name__ == "__main__":
    asyncio.run(main())
