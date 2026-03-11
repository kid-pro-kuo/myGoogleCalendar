from sqlalchemy import create_engine, select, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

engine = create_engine("sqlite:///shift_database.sqlite3", echo=True)


class Base(DeclarativeBase):
    pass


class SeenShift(Base):
    __tablename__ = "seen_shifts"
    id: Mapped[int] = mapped_column(primary_key=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(255), primary_key=True)
    value: Mapped[str] = mapped_column(String(4096), default="")


with Session(engine) as session:
    Base.metadata.create_all(engine)
    session.commit()


def get_setting(key, default=""):
    with Session(engine) as session:
        result = session.scalar(select(Setting).filter(Setting.key == key))
        return result.value if result else default


def set_setting(key, value):
    with Session(engine) as session:
        existing = session.scalar(select(Setting).filter(Setting.key == key))
        if existing:
            existing.value = value
        else:
            session.add(Setting(key=key, value=value))
        session.commit()
