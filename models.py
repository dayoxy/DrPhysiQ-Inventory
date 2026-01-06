from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Text,
    func,
    Boolean
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


# ================= USER =================
class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    full_name = Column(String, nullable=False)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin | staff

    sbu_id = Column(String(36), ForeignKey("sbus.id"), nullable=True)

    is_active = Column(Boolean, default=True)  # ✅ ADD THIS

    created_at = Column(DateTime, server_default=func.now())

    sbu = relationship("SBU", back_populates="staff")



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

    staff = relationship("User", back_populates="sbu")
    sales = relationship("Sale", back_populates="sbu")
    expenses = relationship("Expense", back_populates="sbu")


# ================= SALE =================
class Sale(Base):
    __tablename__ = "sales"

    id = Column(String, primary_key=True)
    sbu_id = Column(String, ForeignKey("sbus.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    date = Column(Date, nullable=False)
    notes = Column(Text)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
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
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    sbu = relationship("SBU", back_populates="expenses")
    staff = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"))
    action = Column(String(255), nullable=False)
    entity = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

