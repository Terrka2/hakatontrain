from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import User, UserCreate

engine = create_engine(str(settings.DATABASE_URL), pool_pre_ping=True)


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    # Демо-пользователи CityTriage: руководитель и три бригады из fixture (c1–c3).
    demo_users = [
        ("supervisor@demo.md", "Руководитель службы", "supervisor", None),
        ("crew1@demo.md", "Бригадир · Дорожная №1", "crew", "c1"),
        ("crew2@demo.md", "Бригадир · Электрики + зелёное хозяйство", "crew", "c2"),
        ("crew3@demo.md", "Бригадир · Санитарная + водоканал", "crew", "c3"),
    ]
    for email, full_name, role, crew_id in demo_users:
        if session.exec(select(User).where(User.email == email)).first():
            continue
        crud.create_user(
            session=session,
            user_create=UserCreate(
                email=email,
                password=settings.DEMO_PASSWORD,
                full_name=full_name,
                role=role,
                crew_id=crew_id,
            ),
        )
