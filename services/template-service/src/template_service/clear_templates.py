#!/usr/bin/env python3
"""Clear all templates from database - preparing for production templates"""
import asyncio
import asyncpg
import os

async def clear_templates():
    # Use same connection string as app
    db_url = os.getenv('POSTGRES_URL', 'postgresql://postgres:postgres@localhost:15432/maestro_registry')

    print(f"Connecting to: {db_url}")

    try:
        conn = await asyncpg.connect(db_url)

        # Get count before
        count_before = await conn.fetchval('SELECT COUNT(*) FROM templates')
        print(f"Templates before: {count_before}")

        # Delete all
        await conn.execute('DELETE FROM templates')

        # Get count after
        count_after = await conn.fetchval('SELECT COUNT(*) FROM templates')
        print(f"Templates after: {count_after}")
        print(f"✅ Deleted {count_before} templates")

        await conn.close()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(clear_templates())
