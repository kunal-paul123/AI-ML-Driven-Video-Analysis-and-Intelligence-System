import asyncio
from sqlalchemy import text
from app.database import engine

async def alter_table():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE alert_history ADD COLUMN screenshot_path VARCHAR(255);"))
            print("Successfully added 'screenshot_path' column to 'alert_history' table.")
        except Exception as e:
            print(f"Error or column already exists: {e}")

if __name__ == "__main__":
    asyncio.run(alter_table())
