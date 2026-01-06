from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
import uuid

from database import get_db
from models import User, Sale, Expense, SBU
from auth import verify_password, create_access_token, get_current_user, hash_password
from schemas import (
    CreateStaffSchema,
    CreateSBUSchema,
    LoginSchema,
    SaleCreateSchema,
    StaffExpenseSchema,
    StaffDashboardResponse,
    DailyReportResponse,
    ChartResponse,
    StaffContributionSchema,
    SBUReportWithStaffSchema
)

# ---------------- APP ----------------
app = FastAPI(
    title="DrPhysiQ Inventory API",
    swagger_ui_parameters={"persistAuthorization": True}
)

# ---------------- CORS ----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://drphysi.netlify.app"
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- LOGIN ----------------
@app.post("/login")
def login(payload: LoginSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({
        "sub": user.id,
        "role": user.role
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username
    }

# ---------------- ADMIN: CREATE STAFF ----------------
@app.post("/admin/create-staff")
def create_staff(
    payload: CreateStaffSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="User already exists")

    user = User(
        id=str(uuid.uuid4()),
        full_name=payload.full_name,
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="staff",
        sbu_id=payload.sbu_id
    )

    db.add(user)
    db.commit()
    return {"message": "Staff created successfully"}

# ---------------- ADMIN: CREATE SBU ----------------
@app.post("/admin/create-sbu")
def create_sbu(
    payload: CreateSBUSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    sbu = SBU(
        id=str(uuid.uuid4()),
        name=payload.name,
        department=payload.department,
        daily_budget=payload.daily_budget,
        description=payload.description
    )

    db.add(sbu)
    db.commit()
    return {"message": "SBU created successfully"}

# ---------------- STAFF: SALES ----------------
@app.post("/staff/sales")
def create_or_update_sales(
    payload: SaleCreateSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    if not current_user.sbu_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    # 🔍 Check if sale already exists for this SBU + date
    sale = (
        db.query(Sale)
        .filter(
            Sale.sbu_id == current_user.sbu_id,
            Sale.date == payload.sale_date
        )
        .first()
    )

    if sale:
        # ✅ UPDATE existing sale
        sale.amount = payload.amount
        sale.notes = payload.notes
    else:
        # ✅ INSERT new sale
        sale = Sale(
            id=str(uuid4()),
            sbu_id=current_user.sbu_id,
            amount=payload.amount,
            date=payload.sale_date,
            notes=payload.notes,
            created_by=current_user.id
        )
        db.add(sale)

    db.commit()

    return {
        "message": "Sales saved successfully",
        "date": payload.sale_date,
        "amount": payload.amount
    }

# ---------------- STAFF: EXPENSE ----------------
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
    return {"message": "Expense recorded"}

# ---------------- STAFF DASHBOARD ----------------
@app.get("/staff/my-sbu", response_model=StaffDashboardResponse)
def staff_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

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
        .filter(Expense.sbu_id == sbu.id, Expense.effective_from == today)
        .group_by(Expense.category)
        .all()
    )

    variable_costs = {k: 0 for k in ["consumables", "general_expenses", "utilities", "miscellaneous"]}
    for cat, amt in variable_rows:
        variable_costs[cat] = amt

    fixed_total = (sbu.personnel_cost or 0) + (sbu.rent or 0) + (sbu.electricity or 0)
    total_expenses = fixed_total + sum(variable_costs.values())
    net_profit = sales_today - total_expenses

    performance = round((sales_today / sbu.daily_budget) * 100, 2) if sbu.daily_budget else 0
    status = "Excellent" if performance >= 100 else "warning" if performance >= 80 else "Critical"

    return {
        "sbu": {"id": sbu.id, "name": sbu.name, "daily_budget": sbu.daily_budget},
        "sales_today": sales_today,
        "fixed_costs": {
            "personnel_cost": sbu.personnel_cost or 0,
            "rent": sbu.rent or 0,
            "electricity": sbu.electricity or 0,
            "total_fixed": fixed_total
        },
        "variable_costs": variable_costs,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "performance_percent": performance,
        "performance_status": status
    }

# ---------------- ADMIN REPORT ----------------
@app.get(
    "/admin/sbu-report",
    response_model=SBUReportWithStaffSchema
)
def admin_sbu_report(
    sbu_id: str,
    period: str,
    report_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    # ---- totals ----
    total_sales = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(Sale.sbu_id == sbu_id)
        .scalar()
    )

    total_expenses = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.sbu_id == sbu_id)
        .scalar()
    )

    net_profit = total_sales - total_expenses
    performance = round((total_sales / 1) * 100, 2)  # adjust if you use budget

    # ---- staff breakdown ----
    staff_rows = (
        db.query(
            User.id,
            User.full_name,
            func.coalesce(func.sum(Sale.amount), 0).label("sales"),
            func.coalesce(func.sum(Expense.amount), 0).label("expenses")
        )
        .join(Sale, Sale.created_by == User.id, isouter=True)
        .join(Expense, Expense.created_by == User.id, isouter=True)
        .filter(User.sbu_id == sbu_id)
        .group_by(User.id)
        .all()
    )

    staff_breakdown = [
        {
            "staff_id": s.id,
            "staff_name": s.full_name,
            "total_sales": s.sales,
            "total_expenses": s.expenses,
            "net_profit": s.sales - s.expenses
        }
        for s in staff_rows
    ]

    return {
        "period": period,
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "performance_percent": performance,
        "staff_breakdown": staff_breakdown
    }

@app.get("/admin/sbus")
def list_sbus(
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
            "daily_budget": sbu.daily_budget
        }
        for sbu in sbus
    ]


# ---------------- ADMIN CHART (SAFE STUB) ----------------
@app.get("/admin/sbu-chart", response_model=ChartResponse)
def get_sbu_chart():
    return {"labels": [], "sales": [], "expenses": []}

@app.patch("/admin/staff/{staff_id}/deactivate")
def deactivate_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    staff = db.query(User).filter(User.id == staff_id, User.role == "staff").first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    staff.is_active = False
    db.commit()

    return {"message": "Staff deactivated successfully"}
    
@app.patch("/admin/staff/{staff_id}/activate")
def activate_staff(
    staff_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    staff = db.query(User).filter(User.id == staff_id, User.role == "staff").first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    staff.is_active = True
    db.commit()

    return {"message": "Staff activated successfully"}

@app.get("/admin/staff")
def list_staff(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    staff = db.query(User).filter(User.role == "staff").all()

    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "username": u.username,
            "sbu_id": u.sbu_id,
            "is_active": u.is_active,
            "created_at": u.created_at
        }
        for u in staff
    ]


@app.get("/staff/expenses/history")
def get_staff_expense_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403, detail="Staff only")

    if not current_user.sbu_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    rows = (
        db.query(
            Expense.effective_from,
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .filter(Expense.sbu_id == current_user.sbu_id)
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

@app.get("/admin/staff/{staff_id}/sbu-report")
def admin_staff_sbu_report(
    staff_id: str,
    period: str,
    report_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")

    staff = db.query(User).filter(
        User.id == staff_id,
        User.role == "staff"
    ).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    if not staff.sbu_id:
        raise HTTPException(status_code=400, detail="Staff not assigned to SBU")

    sbu = db.query(SBU).filter(SBU.id == staff.sbu_id).first()
    if not sbu:
        raise HTTPException(status_code=404, detail="SBU not found")

    # 📆 DATE RANGE
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

    # 💰 SALES
    total_sales = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(
            Sale.sbu_id == sbu.id,
            Sale.date >= start,
            Sale.date <= end
        )
        .scalar()
    )

    # 💸 VARIABLE EXPENSES
    variable_rows = (
        db.query(
            Expense.category,
            func.coalesce(func.sum(Expense.amount), 0)
        )
        .filter(
            Expense.sbu_id == sbu.id,
            Expense.effective_from >= start,
            Expense.effective_from <= end
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

    # 🔒 FIXED COSTS
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
        "staff": {
            "id": staff.id,
            "name": staff.full_name
        },
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
        "fixed_expenses": fixed_total,
        "variable_expenses": variable_expenses,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "performance_percent": performance
    }



# ---------------- SWAGGER AUTH ----------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="DrPhysiQ Inventory API",
        version="1.0.0",
        description="Admin & Staff API",
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi










