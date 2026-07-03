"""
Seed demo data for testing and development.

This script creates sample users with accounts and some initial transfers
to demonstrate the system's functionality.

Run: python seed_demo_data.py
"""

import asyncio
import uuid
import asyncpg
from datetime import datetime, timedelta
import os
import sys

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.security import hash_password

DATABASE_DSN = os.getenv(
    "DATABASE_DSN", 
    os.getenv("DATABASE_URL", "postgresql://vaultly:vaultly_dev@localhost:5433/vaultly")
)

DEMO_USERS = [
    {
        "email": "alice@demo.vaultly",
        "handle": "alice",
        "full_name": "Alice Johnson",
        "password": "demo123",
        "balance": 50000,  # $500.00
    },
    {
        "email": "bob@demo.vaultly",
        "handle": "bob", 
        "full_name": "Bob Smith",
        "password": "demo123",
        "balance": 25000,  # $250.00
    },
    {
        "email": "charlie@demo.vaultly",
        "handle": "charlie",
        "full_name": "Charlie Brown",
        "password": "demo123",
        "balance": 100000,  # $1000.00
    },
    {
        "email": "diana@demo.vaultly",
        "handle": "diana",
        "full_name": "Diana Prince",
        "password": "demo123",
        "balance": 75000,  # $750.00
    },
]


async def seed_data():
    """Create demo users with accounts and initial transfers."""
    print("Connecting to database...")
    pool = await asyncpg.create_pool(DATABASE_DSN)
    
    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                print("Creating demo users...")
                
                user_ids = {}
                account_ids = {}
                
                for user_data in DEMO_USERS:
                    # Check if user already exists
                    existing = await conn.fetchrow(
                        "SELECT id FROM users WHERE email = $1 OR handle = $2",
                        user_data["email"],
                        user_data["handle"]
                    )
                    
                    if existing:
                        print(f"  User {user_data['handle']} already exists, skipping...")
                        user_id = existing["id"]
                    else:
                        # Create user
                        user_id = await conn.fetchval(
                            """INSERT INTO users (email, handle, full_name, password_hash)
                               VALUES ($1, $2, $3, $4) RETURNING id""",
                            user_data["email"],
                            user_data["handle"],
                            user_data["full_name"],
                            hash_password(user_data["password"]),
                        )
                        print(f"  Created user: {user_data['handle']}")
                    
                    user_ids[user_data["handle"]] = user_id
                    
                    # Get or create account
                    account = await conn.fetchrow(
                        "SELECT id FROM accounts WHERE user_id = $1 AND type = 'wallet'",
                        user_id
                    )
                    
                    account_exists = account is not None
                    
                    if account:
                        account_id = account["id"]
                        print(f"    Account already exists")
                    else:
                        account_id = await conn.fetchval(
                            "INSERT INTO accounts (user_id, balance) VALUES ($1, $2) RETURNING id",
                            user_id,
                            user_data["balance"],
                        )
                        print(f"    Created account with ${user_data['balance']/100:.2f}")
                    
                    account_ids[user_data["handle"]] = account_id
                    
                    # Seed balance through system transfer if needed
                    if user_data["balance"] > 0 and not account_exists:
                        await conn.execute(
                            """
                            WITH t AS (
                                INSERT INTO transfers (idempotency_key, from_account, to_account, amount, note)
                                SELECT $3, id, $1, $2, 'demo seed' FROM accounts WHERE type = 'system' LIMIT 1
                                RETURNING id
                            )
                            INSERT INTO ledger_entries (transfer_id, account_id, amount)
                            SELECT id, $1, $2 FROM t
                            """,
                            account_id,
                            user_data["balance"],
                            f"seed-{account_id}",
                        )
                        print(f"    Seeded balance through ledger")
                
                print("\nCreating sample transfers...")
                
                # Create some sample transfers between users
                sample_transfers = [
                    ("alice", "bob", 2500, "Coffee money"),  # $25.00
                    ("bob", "charlie", 5000, "Thanks for lunch!"),  # $50.00
                    ("charlie", "diana", 10000, "Project payment"),  # $100.00
                    ("diana", "alice", 1500, "Book club"),  # $15.00
                    ("alice", "charlie", 7500, "Gift"),  # $75.00
                ]
                
                for from_handle, to_handle, amount, note in sample_transfers:
                    from_account = account_ids[from_handle]
                    to_account = account_ids[to_handle]
                    
                    # Check if similar transfer already exists
                    existing = await conn.fetchrow(
                        """SELECT id FROM transfers 
                           WHERE from_account = $1 AND to_account = $2 AND amount = $3""",
                        from_account, to_account, amount
                    )
                    
                    if existing:
                        print(f"  Transfer {from_handle} -> {to_handle} already exists, skipping...")
                        continue
                    
                    # Execute transfer
                    transfer_id = await conn.fetchval(
                        """INSERT INTO transfers (idempotency_key, from_account, to_account, amount, note)
                           VALUES ($1, $2, $3, $4, $5) RETURNING id""",
                        f"demo-{uuid.uuid4()}",
                        from_account,
                        to_account,
                        amount,
                        note,
                    )
                    
                    # Create ledger entries
                    await conn.execute(
                        """INSERT INTO ledger_entries (transfer_id, account_id, amount)
                           VALUES ($1, $2, $3), ($1, $4, $5)""",
                        transfer_id, from_account, -amount, to_account, amount,
                    )
                    
                    # Update balances
                    await conn.execute(
                        "UPDATE accounts SET balance = balance - $2 WHERE id = $1",
                        from_account, amount,
                    )
                    await conn.execute(
                        "UPDATE accounts SET balance = balance + $2 WHERE id = $1",
                        to_account, amount,
                    )
                    
                    print(f"  Created transfer: {from_handle} -> ${amount/100:.2f} -> {to_handle}")
                
                print("\n✅ Demo data seeded successfully!")
                print("\nDemo accounts:")
                for user_data in DEMO_USERS:
                    print(f"  @{user_data['handle']} / {user_data['password']}")
                
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(seed_data())
