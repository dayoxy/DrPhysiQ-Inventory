from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Boolean,
    func
)
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime


# ================= USER =================
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    full_name = Column(String(150), nullable=False)  # ✅ ADD THIS
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)

    must_change_password = Column(Boolean, default=True)

    sbu_id = Column(String, ForeignKey("sbus.id"), nullable=True)
    sbu = relationship("SBU", back_populates="staff")

    created_at = Column(DateTime, default=datetime.utcnow)


# ================= SBU =================
class SBU(Base):
    __tablename__ = "sbus"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    department = Column(String, nullable=False)
    daily_budget = Column(Integer, nullable=False)
    description = Column(Text)

    # Fixed costs
    personnel_cost = Column(Integer, default=0)
    rent = Column(Integer, default=0)
    electricity = Column(Integer, default=0)

    staff = relationship("User", back_populates="sbu", cascade="all,delete")
    sales = relationship("Sale", back_populates="sbu", cascade="all,delete")
    expenses = relationship("Expense", back_populates="sbu", cascade="all,delete")


# ================= SALE =================
class Sale(Base):
    __tablename__ = "sales"

    id = Column(String, primary_key=True)
    sbu_id = Column(String, ForeignKey("sbus.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text)

    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())

    sbu = relationship("SBU", back_populates="sales")
    staff = relationship("User")


# ================= EXPENSE =================
class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String, primary_key=True)
    sbu_id = Column(String, ForeignKey("sbus.id"), nullable=False)
    category = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    effective_from = Column(Date, nullable=False)
    notes = Column(Text)

    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())

    sbu = relationship("SBU", back_populates="expenses")
    staff = relationship("User")


# ================= AUDIT LOG =================
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    action = Column(String(255), nullable=False)
    entity = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
