from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
import uuid

from database import get_db
from models import User, Sale, Expense, SBU, AuditLog
from auth import verify_password, create_access_token, get_current_user, hash_password
from schemas import (
    CreateStaffSchema,
    CreateSBUSchema,
    LoginSchema,
    SaleCreateSchema,
    StaffExpenseSchema,
    StaffDashboardResponse,
    ChartResponse,
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
        "https://dayoxy.github.io",
        "https://dayoxy.github.io/DrPhysiQ-Frontend"
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

    token = create_access_token({"sub": user.id, "role": user.role})

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
        raise HTTPException(status_code=403)

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

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        action=f"Created staff {payload.username}",
        entity="staff"
    ))

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
        raise HTTPException(status_code=403)

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
        raise HTTPException(status_code=403)

    sale = (
        db.query(Sale)
        .filter(Sale.sbu_id == current_user.sbu_id, Sale.date == payload.sale_date)
        .first()
    )

    if sale:
        sale.amount = payload.amount
        sale.notes = payload.notes
    else:
        sale = Sale(
            id=str(uuid.uuid4()),
            sbu_id=current_user.sbu_id,
            amount=payload.amount,
            date=payload.sale_date,
            notes=payload.notes,
            created_by=current_user.id
        )
        db.add(sale)

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        action=f"Recorded sale ₦{payload.amount}",
        entity="sale"
    ))

    db.commit()
    return {"message": "Sales saved successfully"}

# ---------------- STAFF: EXPENSE ----------------
@app.post("/staff/expenses")
def create_staff_expense(
    payload: StaffExpenseSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "staff":
        raise HTTPException(status_code=403)

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

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        action=f"Recorded expense ₦{payload.amount}",
        entity="expense"
    ))

    db.commit()
    return {"message": "Expense recorded"}

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
            "is_active": u.is_active
        }
        for u in staff
    ]


# ---------------- STAFF DASHBOARD ----------------
@app.get("/staff/my-sbu", response_model=StaffDashboardResponse)
def staff_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    sbu = db.query(SBU).filter(SBU.id == current_user.sbu_id).first()
    today = date.today()

    sales_today = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(Sale.sbu_id == sbu.id, Sale.date == today)
        .scalar()
    )

    fixed_total = (sbu.personnel_cost or 0) + (sbu.rent or 0) + (sbu.electricity or 0)
    net_profit = sales_today - fixed_total

    performance = (
        round((sales_today / sbu.daily_budget) * 100, 2)
        if sbu.daily_budget else 0
    )

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
        "variable_costs": {},
        "total_expenses": fixed_total,
        "net_profit": net_profit,
        "performance_percent": performance,
        "performance_status": status
    }

# ---------------- ADMIN SBU REPORT (WITH STAFF BREAKDOWN) ----------------
@app.get("/admin/sbu-report", response_model=SBUReportWithStaffSchema)
def admin_sbu_report(
    sbu_id: str,
    period: str,
    report_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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

    total_sales = (
        db.query(func.coalesce(func.sum(Sale.amount), 0))
        .filter(Sale.sbu_id == sbu_id, Sale.date >= start, Sale.date <= end)
        .scalar()
    )

    total_expenses = (
        db.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.sbu_id == sbu_id, Expense.effective_from >= start, Expense.effective_from <= end)
        .scalar()
    )

    net_profit = total_sales - total_expenses

    sales_subq = (
        db.query(Sale.created_by.label("staff_id"), func.sum(Sale.amount).label("sales"))
        .filter(Sale.sbu_id == sbu_id)
        .group_by(Sale.created_by)
        .subquery()
    )

    expense_subq = (
        db.query(Expense.created_by.label("staff_id"), func.sum(Expense.amount).label("expenses"))
        .filter(Expense.sbu_id == sbu_id)
        .group_by(Expense.created_by)
        .subquery()
    )

    staff_rows = (
        db.query(
            User.id,
            User.full_name,
            func.coalesce(sales_subq.c.sales, 0),
            func.coalesce(expense_subq.c.expenses, 0)
        )
        .outerjoin(sales_subq, sales_subq.c.staff_id == User.id)
        .outerjoin(expense_subq, expense_subq.c.staff_id == User.id)
        .filter(User.sbu_id == sbu_id)
        .all()
    )

    staff_breakdown = [
        {
            "staff_id": s.id,
            "staff_name": s.full_name,
            "total_sales": s[2],
            "total_expenses": s[3],
            "net_profit": s[2] - s[3]
        }
        for s in staff_rows
    ]

    return {
        "period": period,
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "net_profit": net_profit,
        "performance_percent": 0,
        "staff_breakdown": staff_breakdown
    }

# ---------------- AUDIT LOGS ----------------
@app.get("/admin/audit-logs")
def get_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logs = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .limit(100)
        .all()
    )

    return [
        {
            "staff": l.user.full_name if l.user else "System",
            "action": l.action,
            "time": l.created_at
        }
        for l in logs
    ]

# ---------------- SWAGGER AUTH ----------------
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="DrPhysiQ Inventory API",
        version="1.0.0",
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return app.openapi_schema

app.openapi = custom_openapi
