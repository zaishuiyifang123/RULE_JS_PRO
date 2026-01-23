import argparse
import getpass
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.admin import Admin


def ensure_tables() -> None:
    Base.metadata.create_all(bind=engine)


def create_admin(
    username: str,
    password: str,
    real_name: str | None,
    phone: str | None,
    email: str | None,
) -> bool:
    db = SessionLocal()
    try:
        exists = (
            db.query(Admin)
            .filter(Admin.username == username, Admin.is_deleted == False)
            .first()
        )
        if exists:
            print(f"admin already exists: {username}")
            return False

        admin = Admin(
            username=username,
            password_hash=hash_password(password),
            real_name=real_name,
            phone=phone,
            email=email,
            status="active",
        )
        db.add(admin)
        db.commit()
        print(f"admin created: {username}")
        return True
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize admin user")
    parser.add_argument("--username", required=True, help="admin username")
    parser.add_argument("--password", required=False, help="admin password")
    parser.add_argument("--real-name", required=False, help="admin real name")
    parser.add_argument("--phone", required=False, help="admin phone")
    parser.add_argument("--email", required=False, help="admin email")
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Admin password: ")

    ensure_tables()
    create_admin(
        username=args.username,
        password=password,
        real_name=args.real_name,
        phone=args.phone,
        email=args.email,
    )


if __name__ == "__main__":
    main()
