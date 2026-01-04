from pydantic import BaseModel, Field
from datetime import date
from typing import Optional

# ================= AUTH =================
class LoginSchema(BaseModel):
    username: str
    password: str


# ================= STAFF =================
class CreateStaffSchema(BaseModel):
    full_name: str
    username: str
    password: str
    department_id: str


# ================= SBU =================
class CreateSBUSchema(BaseModel):
    name: str
    department: str
    daily_budget: int
    description: Optional[str] = None


# ================= SALES =================
class CreateSaleSchema(BaseModel):
    amount: int
    date: Optional[date] = None
    notes: Optional[str] = None


class SalesSchema(BaseModel):
    amount: int
    date: date
    notes: Optional[str] = None

# ================= STAFF EXPENSES =================
class StaffExpenseSchema(BaseModel):
    category: str            # consumables | general | utilities | miscellaneous
    amount: int
    date: date
    notes: Optional[str] = None
