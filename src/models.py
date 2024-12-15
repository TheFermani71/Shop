from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    wallet = Column(Integer, default=1_000)

    orders = relationship("Order", back_populates="user")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(Integer, default=0)
    price = Column(Float, nullable=False)

    # Relationship to orders
    orders = relationship("Order", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)  # Product foreign key
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # User foreign key

    quantity = Column(Integer)
    status = Column(String, default="processing")

    # Relationship to product
    product = relationship("Product", back_populates="orders")
    user = relationship("User", back_populates="orders")


class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, unique=True, index=True)
    status = Column(String, default="processing")
