from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from fastapi import Depends
from fastapi import Security
from fastapi import Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database import get_db
from models import User
from models import Sale
from models import SBU
from auth import verify_password, create_access_token, get_current_user, hash_password
from datetime import date, timedelta
from models import Expense
from sqlalchemy import func, and_
from schemas import CreateStaffSchema, CreateSBUSchema, LoginSchema, SaleCreateSchema, StaffExpenseSchema, StaffDashboardResponse, DailyReportResponse, ChartResponse
import uuid
from uuid import uuid4




# ✅ APP MUST BE DEFINED BEFORE ROUTES
app = FastAPI(title="Inventory System API", swagger_ui_parameters={"persistAuthorization": True})

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "DrPhysiQ Inventory API",
        "version": "1.0.0"
    }



app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://drphysi.netlify.app"  # 👈 your Netlify URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



@app.options("/{path:path}")
def options_handler(path: str):
    return {}


# -----------------------
# LOGIN
# -----------------------
@app.post("/login")
def login(payload: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": user.id,      # ✅ REQUIRED
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }


# -----------------------
# ADMIN: CREATE STAFF
# -----------------------
@app.post("/admin/create-staff")
def create_staff(
    payload: CreateStaffSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # Check duplicate username
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        id=str(uuid.uuid4()),
        full_name=payload.full_name,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="staff",
        department_id=payload.department_id
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {"message": "Staff created successfully"}


# ================= ADMIN: CREATE SBU =================
@app.post("/admin/create-sbu")
def create_sbu(
    payload: CreateSBUSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sbu = SBU(
        id=str(uuid4()),
        name=payload.name,
        department=payload.department,
        daily_budget=payload.daily_budget,
        description=payload.description
    )

    db.add(sbu)
    db.commit()

    return {"message": "SBU created successfully"}


@app.post("/staff/sales")
def create_sale(
    payload: SaleCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    if not current_user.sbu_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    sale = Sale(
        id=str(uuid.uuid4()),
        sbu_id=current_user.sbu_id,
        amount=payload.amount,
        date=payload.sale_date,
        notes=payload.notes,
        created_by=current_user.id
    )

    db.add(sale)
    db.commit()

    return {"message": "Sale recorded successfully"}
    
@app.post("/admin/set-expense")
def set_fixed_expense(
    department_id: str,
    category: str,
    amount: int,
    effective_from: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    expense = Expense(
        id=str(uuid.uuid4()),
        department_id=department_id,
        category=category,
        amount=amount,
        effective_from=effective_from,
        created_by=current_user.id
    )

    db.add(expense)
    db.commit()

    return {"message": "Expense set successfully"}

@app.get("/expenses/active")
def get_active_expenses(
    department_id: str,
    on_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    expenses = (
        db.query(Expense)
        .filter(
            Expense.department_id == department_id,
            Expense.effective_from <= on_date
        )
        .all()
    )

    total = sum(e.amount for e in expenses)

    return {
        "expenses": expenses,
        "total_expenses": total
    }

@app.get(
    "/report/daily",
    response_model=DailyReportResponse
)
def daily_report(
    department_id: str,
    report_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sales_total = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(Sale.sbu_id == department_id, Sale.date == report_date)
        .scalar()
    )

    expenses_total = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.sbu_id == department_id,
            Expense.effective_from <= report_date
        )
        .scalar()
    )

    return {
        "date": report_date,
        "sales": sales_total,
        "expenses": expenses_total,
        "net_profit": sales_total - expenses_total
    }


@app.get("/admin/staff")
def get_all_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        return {"detail": "Not authorized"}

    staff = db.query(User).filter(User.role == "staff").all()

    return [
        {
            "id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "department": user.department,
            "created_at": user.created_at
        }
        for user in staff
    ]

@app.post("/staff/sales")
def create_or_update_sales(
    payload: SalesSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    today = date.today()

    sale = (
        db.query(Sale)
        .filter(
            Sale.sbu_id == current_user.department_id,
            Sale.date == today
        )
        .first()
    )

    if sale:
        sale.amount = payload.amount
        sale.notes = payload.notes
    else:
        sale = Sale(
            id=str(uuid4()),
            sbu_id=current_user.department_id,
            amount=payload.amount,
            date=today,
            notes=payload.notes,
            created_by=current_user.id
        )
        db.add(sale)

    db.commit()

    return {
        "message": "Sales saved",
        "amount": sale.amount,
        "date": today
    }



@app.get("/admin/sbus")
def get_all_sbus(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sbus = db.query(SBU).all()

    return [
        {
            "id": sbu.id,
            "name": sbu.name,
            "department": sbu.department,
            "daily_budget": sbu.daily_budget,
            "description": sbu.description
        }
        for sbu in sbus
    ]

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="DrPhysiQ SBU System",
        version="1.0.0",
        description="Admin & Staff API",
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }

    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi



@app.get(
    "/staff/my-sbu",
    response_model=StaffDashboardResponse
)
def get_staff_sbu_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    if not current_user.sbu_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    sbu = db.query(SBU).filter(SBU.id == current_user.sbu_id).first()
    if not sbu:
        raise HTTPException(status_code=404, detail="SBU not found")

    today = date.today()

    sales_today = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(Sale.sbu_id == sbu.id, Sale.date == today)
        .scalar()
    )

    variable_rows = (
        db.query(Expense.category, func.coalesce(func.sum(Expense.amount), 0))
        .filter(
            Expense.sbu_id == sbu.id,
            Expense.effective_from == today
        )
        .group_by(Expense.category)
        .all()
    )

    variable_costs = {
        "consumables": 0,
        "general_expenses": 0,
        "utilities": 0,
        "miscellaneous": 0
    }

    for cat, amt in variable_rows:
        variable_costs[cat] = amt

    personnel = sbu.personnel_cost or 0
    rent = sbu.rent or 0
    electricity = sbu.electricity or 0
    fixed_total = personnel + rent + electricity

    variable_total = sum(variable_costs.values())
    total_expenses = fixed_total + variable_total
    net_profit = sales_today - total_expenses

    performance = (
        round((sales_today / sbu.daily_budget) * 100, 2)
        if sbu.daily_budget > 0 else 0
    )

    status = (
        "Excellent" if performance >= 100
        else "warning" if performance >= 80
        else "Critical"
    )

    return {
        "sbu": {
            "id": sbu.id,
            "name": sbu.name,
            "daily_budget": sbu.daily_budget
        },
        "sales_today": sales_today,
        "fixed_costs": {
            "personnel_cost": personnel,
            "rent": rent,
            "electricity": electricity,
            "total_fixed": fixed_total
        },
        "variable_costs": variable_costs,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "performance_percent": performance,
        "performance_status": status
    }




@app.get("/admin/sbu-report")
def get_sbu_report(
    sbu_id: str,
    period: str,
    report_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sbu = db.query(SBU).filter(SBU.id == sbu_id).first()
    if not sbu:
        raise HTTPException(status_code=404, detail="SBU not found")

    # ---- DATE RANGE ----
    if period == "daily":
        start = report_date
        end = report_date

    elif period == "weekly":
        start = report_date - timedelta(days=6)
        end = report_date

    elif period == "monthly":
        start = report_date.replace(day=1)
        end = report_date

    else:
        raise HTTPException(status_code=400, detail="Invalid period")

    # ---- SALES ----
    total_sales = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(
            Sale.sbu_id == sbu.id,
            Sale.date >= start,
            Sale.date <= end
        )
        .scalar()
    )

    # ---- EXPENSES (FIXED COSTS) ----
    personnel = sbu.personnel_cost or 0
    rent = sbu.rent or 0
    electricity = sbu.electricity or 0

    total_expenses = personnel + rent + electricity
    net_profit = total_sales - total_expenses

    performance = (
        round((total_sales / sbu.daily_budget) * 100, 2)
        if sbu.daily_budget > 0 else 0
    )

    return {
        "sbu": {
            "id": sbu.id,
            "name": sbu.name
        },
        "period": period,
        "date_range": {
            "from": start,
            "to": end
        },
        "total_sales": total_sales,
        "expenses": {
            "personnel": personnel,
            "rent": rent,
            "electricity": electricity,
            "total": total_expenses
        },
        "net_profit": net_profit,
        "performance_percent": performance
    }


@app.get(
    "/admin/sbu-chart",
    response_model=ChartResponse
)
def get_sbu_chart(
    sbu_id: str,
    period: str,
    report_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # (logic unchanged)
    return {
        "labels": labels,
        "sales": sales_data,
        "expenses": expense_data
    }



@app.post("/staff/expenses")
def create_staff_expense(
    payload: StaffExpenseSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    if not current_user.sbu_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    expense = Expense(
        id=str(uuid.uuid4()),
        sbu_id=current_user.sbu_id,
        category=payload.category,
        amount=payload.amount,
        effective_from=payload.date,
        notes=payload.notes,
        created_by=current_user.id
    )

    db.add(expense)
    db.commit()

    return {"message": "Expense recorded successfully"}


@app.get("/staff/expenses/history")
def get_staff_expense_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    if not current_user.department_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    rows = (
        db.query(
            Expense.effective_from,
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .filter(Expense.sbu_id == current_user.department_id)
        .group_by(Expense.effective_from, Expense.category)
        .order_by(Expense.effective_from.desc())
        .all()
    )

    history = {}

    for day, category, amount in rows:
        day_str = day.isoformat()

        if day_str not in history:
            history[day_str] = {
                "consumables": 0,
                "general_expenses": 0,
                "utilities": 0,
                "miscellaneous": 0
            }

        history[day_str][category] = amount

    return history


@app.get("/admin/sbu-report")
def admin_sbu_report(
    sbu_id: str = Query(...),
    period: str = Query("monthly"),
    report_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sbu = db.query(SBU).filter(SBU.id == sbu_id).first()
    if not sbu:
        raise HTTPException(status_code=404, detail="SBU not found")

    # 📆 Month range
    start_date = report_date.replace(day=1)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)

    # 🔹 SALES
    total_sales = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(
            Sale.sbu_id == sbu.id,
            Sale.date >= start_date,
            Sale.date < end_date
        )
        .scalar()
    )

    # 🔹 VARIABLE EXPENSES (STAFF)
    variable_rows = (
        db.query(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .filter(
            Expense.sbu_id == sbu.id,
            Expense.effective_from >= start_date,
            Expense.effective_from < end_date
        )
        .group_by(Expense.category)
        .all()
    )

    variable_expenses = {
        "consumables": 0,
        "general_expenses": 0,
        "utilities": 0,
        "miscellaneous": 0
    }

    for cat, amt in variable_rows:
        variable_expenses[cat] = amt

    variable_total = sum(variable_expenses.values())

    # 🔹 FIXED COSTS (monthly)
    fixed_total = (
        (sbu.personnel_cost or 0) +
        (sbu.rent or 0) +
        (sbu.electricity or 0)
    )

    total_expenses = fixed_total + variable_total
    net_profit = total_sales - total_expenses

    performance = (
        round((total_sales / sbu.daily_budget) * 100, 2)
        if sbu.daily_budget else 0
    )

    return {
        "period": "monthly",
        "month": start_date.strftime("%B %Y"),
        "sbu": {
            "id": sbu.id,
            "name": sbu.name
        },
        "total_sales": total_sales,
        "fixed_expenses": fixed_total,
        "variable_expenses": variable_expenses,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "performance_percent": performance
    }
