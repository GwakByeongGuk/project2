import base64, io
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from fastapi import FastAPI, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from matplotlib import pyplot as plt
from starlette.requests import Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse
from app.model import models, database
from fastapi import HTTPException
from datetime import datetime
from app.model.models import User
from app.model.database import get_db

app = FastAPI()

# Jinja2 템플릿 설정
templates = Jinja2Templates(directory="views/templates")

# 애플리케이션 시작 시 DB 테이블 생성
@app.on_event("startup")
def on_startup():
    database.init_db()

@app.get("/", response_class=HTMLResponse)
async def read_main(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/admin-login")
async def admin_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(database.get_db)):
    admin = db.query(models.Admin).filter(models.Admin.id == username).first()

    if admin and admin.passwd == password:
        return RedirectResponse(url="/admin-dashboard", status_code=303)

    return HTMLResponse(content="로그인 실패: 아이디 또는 비밀번호가 잘못되었습니다.", status_code=401)

@app.post("/approve-login")
async def admin_login(username2: str = Form(...), password2: str = Form(...), db: Session = Depends(database.get_db)):
    admin = db.query(models.Admin).filter(models.Admin.id == username2).first()

    if admin and admin.passwd == password2:
        return RedirectResponse(url="/user-dashboard", status_code=303)

    return HTMLResponse(content="로그인 실패: 아이디 또는 비밀번호가 잘못되었습니다.", status_code=401)

@app.post("/visitor-register")
async def visitor_register(
        name: str = Form(...),
        email: str = Form(...),
        phone: str = Form(...),
        ob: str = Form(...),
        aname: str = Form(...),
        job: str = Form(...),
        db: Session = Depends(database.get_db)
):
    new_visitor = models.User(
        name=name,
        email=email,
        phone=phone,
        ob=ob,
        aname=aname,
        job=job,
        status=models.Status.PENDING
    )
    db.add(new_visitor)
    db.commit()
    db.refresh(new_visitor)

    return RedirectResponse(url="/user-dashboard", status_code=303)

@app.get("/user-dashboard/{user_id}", response_class=HTMLResponse)
async def user_dashboard(user_id: int, request: Request, db: Session = Depends(database.get_db)):
    visitor = db.query(models.User).filter(models.User.uno == user_id).first()
    if not visitor:
        return HTMLResponse(content="신청 내역을 찾을 수 없습니다.", status_code=404)

    return templates.TemplateResponse("user_dashboard.html", {"request": request, "visitor": visitor})

@app.post("/admin-reject/{uno}")
async def admin_reject(uno: int, db: Session = Depends(database.get_db)):
    visitor = db.query(models.User).filter(models.User.uno == uno).first()
    if visitor:
        visitor.status = "REJECTED"
        db.commit()
    return RedirectResponse(url="/admin-dashboard", status_code=303)

# 관리자 대시보드
@app.get("/admin-dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(database.get_db)):
    pending_visitors = db.query(models.User).filter(models.User.status == "PENDING").all()
    return templates.TemplateResponse("admin_dashboard.html", {"request": request, "pending_visitors": pending_visitors})

@app.get("/user-dashboard", response_class=HTMLResponse)
async def user_dashboard(request: Request, db: Session = Depends(database.get_db)):
    visitors = db.query(models.User).all()

    return templates.TemplateResponse("user_dashboard.html", {"request": request, "visitors": visitors})

@app.get("/visitor-list", response_class=HTMLResponse)
async def visitor_list(request: Request, db: Session = Depends(database.get_db)):
    visitors = db.query(models.User).all()
    return templates.TemplateResponse("visitor_list.html", {"request": request, "visitors": visitors})

@app.get("/statistics", response_class=HTMLResponse)
async def statistics_page(request: Request, db: Session = Depends(database.get_db)):
    logs = db.query(models.EntryExitLog).all()

    # 총 방문자 수
    total_visitors = len(logs)

    # 평균 방문 시간 계산 (초 단위에서 분 단위로 변환)
    total_duration = 0
    count = 0
    for log in logs:
        if log.entry_time and log.exit_time:
            duration = (log.exit_time - log.entry_time).total_seconds() / 60  # 분으로 변환
            total_duration += duration
            count += 1
    avg_visit_duration = total_duration / count if count > 0 else 0

    # 요일별 방문자 수 계산
    weekday_visitors = [0] * 7  # 0: 월요일, 6: 일요일
    for log in logs:
        weekday_visitors[log.entry_time.weekday()] += 1

    # 시간대별 방문자 수 계산
    hour_visitors = [0] * 24
    for log in logs:
        hour_visitors[log.entry_time.hour] += 1

    # 요일별 방문자 수 그래프 생성
    weekdays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    fig, ax = plt.subplots()
    ax.bar(weekdays, weekday_visitors)
    ax.set_title("Number of visitors by day of the week")
    weekday_graph = save_graph_to_base64(fig)

    # 시간대별 방문자 수 그래프 생성
    hours = list(range(24))
    fig, ax = plt.subplots()
    ax.bar(hours, hour_visitors)
    ax.set_title("Number of visitors by time slot")
    hour_graph = save_graph_to_base64(fig)

    return templates.TemplateResponse("statistics.html", {
        "request": request,
        "total_visitors": total_visitors,
        "avg_visit_duration": avg_visit_duration,
        "weekday_graph": weekday_graph,
        "hour_graph": hour_graph
    })


def save_graph_to_base64(fig):
    img = io.BytesIO()
    fig.savefig(img, format='png')
    img.seek(0)
    graph_url = base64.b64encode(img.getvalue()).decode()
    plt.close(fig)
    return f"data:image/png;base64,{graph_url}"

@app.post("/exit/{visitor_id}")
async def log_exit(visitor_id: int, db: Session = Depends(database.get_db)):

    visitor = db.query(models.User).filter(models.User.uno == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="방문자를 찾을 수 없습니다.")

    admin = db.query(models.Admin).filter(models.Admin.ano == 1).first()
    if not admin:
        raise HTTPException(status_code=404, detail="관리자를 찾을 수 없습니다.")

    new_log = models.EntryExitLog(
        name=visitor.name,
        aname=admin.aname,
        createdAt=datetime.now(),
        entry_time=visitor.regdate,
        exit_time=datetime.now()
    )
    db.add(new_log)
    db.commit()

    visitor.status = models.Status.EXIT
    db.commit()

    return JSONResponse(content={"success": True, "message": "퇴입 완료!"})
@app.post("/admin-approve/{visitor_id}")
async def approve_visitor(visitor_id: int, db: Session = Depends(get_db)):
    visitor = db.query(User).filter(User.uno == visitor_id).first()
    if visitor:
        visitor.status = "APPROVED"
        db.commit()

        send_approval_email_sync(visitor.email)

        return JSONResponse(content={"message": "승인되었습니다."}, status_code=200)
    else:
        return JSONResponse(content={"message": "방문자를 찾을 수 없습니다."}, status_code=404)

def send_approval_email_sync(receiver_email):
    sender_email = "teereal@naver.com"
    sender_password = "WEDVPB9ZUMJF"

    subject = "승인 요청이 승인되었습니다"
    body = "당신의 방문 요청이 승인되었습니다. 감사합니다."

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        server = smtplib.SMTP_SSL('smtp.naver.com', 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("이메일이 성공적으로 전송되었습니다.")
    except Exception as e:
        print(f"일반 오류 발생: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

