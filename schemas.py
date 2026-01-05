from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, Dict, List



# ================= AUTH =================
class LoginSchema(BaseModel):
    username: str
    password: str


# ================= USER =================
class CreateStaffSchema(BaseModel):
    full_name: str
    username: str
    password: str
    sbu_id: str


# ================= SBU =================
class CreateSBUSchema(BaseModel):
    name: str
    department: str
    daily_budget: int
    description: Optional[str] = None


# ================= SALES =================
class SaleCreateSchema(BaseModel):
    amount: int = Field(..., gt=0, description="Sale amount")
    sale_date: date = Field(..., description="Date of sale (YYYY-MM-DD)")
    notes: Optional[str] = None


class SaleResponseSchema(BaseModel):
    id: str
    amount: int
    date: date

    class Config:
        from_attributes = True


# ================= EXPENSES =================
class StaffExpenseSchema(BaseModel):
    category: str = Field(
        ...,
        description="consumables | general_expenses | utilities | miscellaneous"
    )
    amount: int = Field(..., gt=0)
    date: date
    notes: Optional[str] = None


class ExpenseResponseSchema(BaseModel):
    id: str
    category: str
    amount: int
    effective_from: date

    class Config:
        from_attributes = True


# ================= REPORTS =================
class DailyReportResponse(BaseModel):
    date: date
    sales: int
    expenses: int
    net_profit: int


class SBUReportResponse(BaseModel):
    period: str
    date_range: Dict[str, date]
    total_sales: int
    total_expenses: int
    net_profit: int
    performance_percent: float


# ================= CHART =================
class ChartResponse(BaseModel):
    labels: List[str]
    sales: List[int]
    expenses: List[int]


class StaffDashboardResponse(BaseModel):
    sbu: Dict[str, str | int]
    sales_today: int
    fixed_costs: FixedCostsSchema
    variable_costs: Dict[str, int]
    total_expenses: int
    net_profit: int
    performance_percent: float
    performance_status: str

