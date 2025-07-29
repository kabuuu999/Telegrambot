import aiosqlite

DB_PATH = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS marriages (
            user1_id INTEGER,
            user2_id INTEGER
        )""")
        await db.commit()

async def add_user(user):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user.id, user.username)
        )
        await db.commit()

async def are_married(user1_id, user2_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM marriages WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
            (user1_id, user2_id, user2_id, user1_id)
        ) as cursor:
            return await cursor.fetchone() is not None

async def create_marriage(user1_id, user2_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO marriages (user1_id, user2_id) VALUES (?, ?)",
            (user1_id, user2_id)
        )
        await db.commit()

async def delete_marriage(user1_id, user2_id):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM marriages WHERE (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)",
            (user1_id, user2_id, user2_id, user1_id)
        )
        await db.commit()

async def get_spouses(user_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT user2_id FROM marriages WHERE user1_id = ? UNION SELECT user1_id FROM marriages WHERE user2_id = ?",
            (user_id, user_id)
        ) as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]
