from sqlalchemy import Column, String, Integer, Text, Date, DateTime, ForeignKey, func, Enum, TIMESTAMP
from sqlalchemy.orm import relationship
from database import Base
import uuid




class Department(Base):
    __tablename__ = "departments"
    id = Column(String(36), primary_key=True)
    name = Column(String(100), unique=True)

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True)
    full_name = Column(String(100))
    username = Column(String(50), unique=True)
    password_hash = Column(String(255))
    role = Column(Enum("admin", "staff"))
    department_id = Column(String(36), ForeignKey("departments.id"))

class SBU(Base):
    __tablename__ = "sbus"

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    daily_budget = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)

    # FIXED COSTS (ADMIN ONLY)
    consumables = Column(Integer, default=0)
    general_expenses = Column(Integer, default=0)
    utilities = Column(Integer, default=0)
    miscellaneous = Column(Integer, default=0)
    personnel_cost = Column(Integer, default=0)
    rent = Column(Integer, default=0)
    electricity = Column(Integer, default=0)

    created_at = Column(DateTime, server_default=func.now())


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True)
    sbu_id = Column(String(36), ForeignKey("sbus.id"), nullable=False)
    category = Column(String(50), nullable=False)
    amount = Column(Integer, nullable=False)
    effective_from = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class Sale(Base):
    __tablename__ = "sales"

    id = Column(String(36), primary_key=True)
    sbu_id = Column(String(36), ForeignKey("sbus.id"), nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    amount = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text)

    created_at = Column(DateTime, server_default=func.now())
