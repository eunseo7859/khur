import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="KHUR | 공대 열람실", page_icon="📚", layout="centered")
DB = Path(os.environ.get("KHUR_DB_PATH", "khur_demo.sqlite3"))
DB.parent.mkdir(parents=True, exist_ok=True)

def connect():
    con = sqlite3.connect(DB, timeout=15)
    con.execute("PRAGMA busy_timeout=15000")
    return con

def init():
    with connect() as con:
        con.execute("CREATE TABLE IF NOT EXISTS seats (id TEXT PRIMARY KEY)")
        con.execute("CREATE TABLE IF NOT EXISTS bookings (seat TEXT PRIMARY KEY REFERENCES seats(id), token TEXT UNIQUE NOT NULL, expires INTEGER NOT NULL)")
        con.executemany("INSERT OR IGNORE INTO seats VALUES (?)", [(f"A{i:02d}",) for i in range(1,21)])

def snapshot(token):
    with connect() as con:
        con.execute("DELETE FROM bookings WHERE expires <= ?", (int(datetime.now().timestamp()),))
        rows=con.execute("SELECT seat,token,expires FROM bookings").fetchall()
    occupied={r[0]:r for r in rows}
    mine=next((r for r in rows if r[1]==token),None)
    return occupied,mine

def book(token,seat):
    con=connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        now=int(datetime.now().timestamp())
        con.execute("DELETE FROM bookings WHERE expires <= ?", (now,))
        row=con.execute("SELECT token FROM bookings WHERE seat=?",(seat,)).fetchone()
        if row and row[0]!=token:
            con.rollback()
            return False,"다른 이용자가 먼저 등록했습니다. 기존 좌석은 유지됩니다."
        if row:
            con.rollback()
            return False,"이미 이용 중인 좌석입니다."
        con.execute("DELETE FROM bookings WHERE token=?",(token,))
        con.execute("INSERT INTO bookings VALUES (?,?,?)",(seat,token,now+7200))
        con.commit()
        return True,f"{seat} 좌석 등록이 완료되었습니다."
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def release(token):
    with connect() as con:
        con.execute("DELETE FROM bookings WHERE token=?",(token,))

init()
if "token" not in st.session_state:
    st.session_state.token=uuid.uuid4().hex
token=st.session_state.token
st.markdown("""<style>
.stApp{background:#faf7f2;} h1,h2,h3{color:#751d32;}
div.stButton > button[kind=primary]{background:#751d32;border-color:#751d32;color:white;}
.block-container{max-width:760px;padding-top:2rem;}
</style>""",unsafe_allow_html=True)
st.title("KHUR")
st.caption("공대 열람실 · 원하는 자리에서 바로 등록하고, 간편하게 변경하세요.")
st.warning("경진대회 시연용입니다. 학교 공식 서비스가 아니며 실제 좌석 예약에 사용하지 마세요.")
if "notice" in st.session_state:
    st.success(st.session_state.pop("notice"))
occupied,mine=snapshot(token)
page=st.radio("메뉴",["좌석 등록·변경","내 좌석","QR 만들기","이용 안내"],horizontal=True)
seats=[f"A{i:02d}" for i in range(1,21)]
requested=st.query_params.get("seat","A01")
if requested not in seats:
    st.error("유효하지 않은 좌석 QR입니다.")
    st.stop()

if page=="좌석 등록·변경":
    st.subheader("공대 열람실")
    st.metric("이용 가능한 좌석",f"{20-len(occupied)} / 20")
    st.caption("입구 ↓ · 예시 배치도(실제 열람실 배치와 다릅니다)")
    for start in range(0,20,4):
        cols=st.columns(4)
        for col,seat in zip(cols,seats[start:start+4]):
            row=occupied.get(seat)
            label="내 좌석" if row and row[1]==token else "이용 중" if row else "이용 가능"
            if col.button(f"{seat}\n{label}",key=seat,use_container_width=True):
                st.query_params["seat"]=seat
                st.rerun()
    st.divider()
    st.subheader(f"선택한 좌석: {requested}")
    if mine:
        st.info(f"현재 내 좌석: {mine[0]} · 다른 빈 좌석을 등록하면 기존 좌석은 자동 반납됩니다.")
    row=occupied.get(requested)
    if row and row[1]==token:
        st.success("현재 이용 중인 좌석입니다.")
    elif row:
        st.error("현재 다른 이용자가 사용 중입니다.")
    elif st.button("이 좌석으로 변경하기" if mine else "이 좌석 이용하기",type="primary",use_container_width=True):
        ok,message=book(token,requested)
        if ok:
            st.session_state.notice=message
            st.rerun()
        else:
            st.error(message)
    if st.button("좌석 현황 새로고침",use_container_width=True):
        st.rerun()

elif page=="내 좌석":
    st.subheader("내 이용 정보")
    if mine:
        st.metric("이용 중인 좌석",mine[0])
        remaining=max(0,(mine[2]-int(datetime.now().timestamp()))//60)
        st.write(f"남은 시간: 약 {remaining}분 · 이용 시간 2시간")
        st.caption("남은 시간은 화면을 새로고침할 때 갱신됩니다.")
        if st.button("좌석 반납하기",type="primary",use_container_width=True):
            release(token)
            st.session_state.notice="좌석을 반납했습니다."
            st.rerun()
    else:
        st.info("현재 이용 중인 좌석이 없습니다.")
    if st.button("이용 정보 새로고침"):
        st.rerun()

elif page=="QR 만들기":
    import io
    from urllib.parse import urlsplit,urlunsplit,urlencode
    import qrcode
    st.subheader("좌석별 QR 생성")
    st.caption("배포가 완료된 앱 주소를 입력하세요. QR에는 좌석 번호만 포함됩니다.")
    base=st.text_input("배포된 KHUR 주소",placeholder="https://your-app.streamlit.app")
    target=st.selectbox("QR을 만들 좌석",seats)
    if base:
        parts=urlsplit(base.strip())
        if parts.scheme not in ("http","https") or not parts.netloc:
            st.error("http:// 또는 https://로 시작하는 앱 주소를 입력하세요.")
        else:
            link=urlunsplit((parts.scheme,parts.netloc,parts.path,urlencode({"seat":target}),""))
            out=io.BytesIO()
            qrcode.make(link).save(out,format="PNG")
            st.image(out.getvalue(),caption=f"KHUR · {target}",width=240)
            st.code(link,language=None)
            st.download_button("QR 이미지 다운로드",out.getvalue(),file_name=f"KHUR_{target}.png",mime="image/png")

else:
    st.subheader("이용 안내")
    st.markdown("""1. 원하는 좌석의 QR을 스캔합니다.
2. 좌석 번호를 확인하고 **이 좌석 이용하기**를 누릅니다.
3. 이동하려면 새 좌석 QR을 스캔한 뒤 **변경하기**를 누릅니다.
4. 이용 종료 시 **내 좌석 → 좌석 반납하기**를 누릅니다.

- 한 세션당 한 좌석, 한 좌석당 한 세션만 등록할 수 있습니다.
- 이용 시간은 2시간이며, 만료 기록은 다음 조회·등록 때 정리됩니다.
- 현황은 자동 갱신되지 않습니다. 최신 상태는 새로고침으로 확인하세요.
- 정적 QR은 현장 방문을 증명하지 않습니다.
""")
st.divider()
st.caption("두리서 · KHUR 데모 | 로그인 없는 브라우저 세션 기반 시제품")
st.caption("새로고침·QR 재접속으로 세션이 바뀌면 기존 이용 정보를 찾지 못할 수 있습니다. 이 경우 기존 좌석은 만료 후 해제됩니다. 배포 서버 재시작 시 데이터도 초기화될 수 있습니다.")
