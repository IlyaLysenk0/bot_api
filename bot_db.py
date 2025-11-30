from sqlalchemy import  Column ,create_engine , String, ForeignKey, Date, DateTime, Boolean, Numeric, BigInteger
from sqlalchemy.orm import DeclarativeBase , sessionmaker, Mapped, mapped_column
from datetime import datetime


engine = create_engine("sqlite:///crypto_info.db", echo=True )

Session = sessionmaker(bind=engine)




class Base(DeclarativeBase):
    def create_db(self):
        Base.metadata.create_all(engine)

    def drop_db(self):
        Base.metadata.drop_all(engine)


class Price(Base):
    __tablename__ = "price"
    id : Mapped[int] = mapped_column(primary_key=True)
    name : Mapped[str] = mapped_column(String(10))
    price = Column(Numeric(precision=18, scale=8))
    date : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Active_users(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)

    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    unique_name: Mapped[str] = mapped_column(String(80))
    tg_name: Mapped[str] = mapped_column(String(80))
    user_language : Mapped[str] = mapped_column(String(10))
    create_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow())

    requests_counter: Mapped[int] = mapped_column(default=0)
    last_request_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

def init_db():
    Base.metadata.create_all(bind=engine)

# Create DB
# base = Base()
# base.create_db()
