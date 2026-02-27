# create_admin.py — MedAssist AI
# ─────────────────────────────────────────────────────────────────
# Run this ONCE on your server to create the first admin account.
# After running, you can log in via the app and manage everything.
# ─────────────────────────────────────────────────────────────────
# Usage:
#   python create_admin.py
# ─────────────────────────────────────────────────────────────────

from dotenv import load_dotenv
load_dotenv()

import bcrypt
from database import SessionLocal, UserCRUD, init_db, test_connection

# ── CONFIG — Change these before running ──────────────────────────
ADMIN_EMAIL    = "King@gmail.com"
ADMIN_PASSWORD = "12345678"
ADMIN_NAME     = "King_Admin"
# ─────────────────────────────────────────────────────────────────

def create_admin():
    print("🏥 MedAssist AI — Admin Bootstrap")
    print("=" * 40)

    # 1. Test DB connection
    if not test_connection():
        print("❌ Cannot connect to database. Check your DATABASE_URL in .env")
        return

    # 2. Make sure tables exist
    init_db()

    db = SessionLocal()

    try:
        # 3. Check if admin already exists
        existing = UserCRUD.get_by_email(db, ADMIN_EMAIL)
        if existing:
            print(f"⚠️  User already exists: {ADMIN_EMAIL}")
            print(f"   Role: {existing.role}")
            if existing.role != "admin":
                existing.role = "admin"
                db.commit()
                print("✅ Role updated to admin!")
            else:
                print("✅ Already an admin. Nothing to do.")
            return

        # 4. Hash password
        hashed = bcrypt.hashpw(
            ADMIN_PASSWORD.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")

        # 5. Create admin user
        user = UserCRUD.create(
            db,
            email         = ADMIN_EMAIL,
            password_hash = hashed,
            full_name     = ADMIN_NAME,
            role          = "admin",
            consent_given = True,
            is_active     = True,
        )

        print(f"✅ Admin created successfully!")
        print(f"   Email   : {user.email}")
        print(f"   Name    : {user.full_name}")
        print(f"   Role    : {user.role}")
        print(f"   ID      : {user.id}")
        print()
        print("🔐 Login credentials:")
        print(f"   Email   : {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")
        print()
        print("⚠️  IMPORTANT: Delete or secure this file after use!")

    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
