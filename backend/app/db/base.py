from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Base.metadata discovers them
import app.models  # noqa: E402, F401
