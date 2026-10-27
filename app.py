import io
import zipfile
from urllib.parse import urlsplit, urlunsplit, urlencode
import streamlit as st
import qrcode
from supabase import create_client

st.set_page_config(page_title="KHUR · 좌석 QR 등록",page_icon="📚",layout="centered")
st.markdown("<style>.stApp{background:#faf7f2}.block-container{max-width:650px}h1,h2,h3{color:#781f36}div.stButton>button[kind=primary]{background:#781f36;border-color:#781f36;color:white}</style>",unsafe_allow_html=True)
st.title("KHUR")
st.caption("두리서 · 공대 열람실 좌석 QR 등록·변경")
st.caption("경진대회 시제품 · 학교 공식 서비스가 아닙니다.")
try:
    url=st.secrets["SUPABASE_URL"]
    key=st.secrets["SUPABASE_ANON_KEY"]
except (KeyError,FileNotFoundError):
    st.info("앱 설정이 필요합니다. README에 따라 Supabase를 만들고 배포 설정의 Secrets에 주소와 공개 키를 입력하세요.")
    st.stop()

# Each Streamlit browser session gets its own client; never share auth clients across users.
if "sb" not in st.session_state:
    st.session_state.sb=create_client(url,key)
sb=st.session_state.sb
seats=[f"A{i:02d}" for i in range(1,21)]
seat=st.query_params.get("seat")
if seat is not None and seat not in seats:
    st.error("등록되지 않은 좌석 QR입니다. 좌석에 붙은 QR을 다시 확인하세요.")
    st.stop()

with st.expander("좌석 QR 출력 도구"):
    st.caption("운영 준비용 공개 도구입니다. 예약 정보나 관리 권한은 노출하지 않습니다.")
    base=st.text_input("배포된 앱 주소",placeholder="https://your-app.streamlit.app")
    if base:
        p=urlsplit(base.strip())
        if p.scheme not in ("https","http") or not p.netloc:
            st.error("올바른 앱 주소를 입력하세요.")
        else:
            qr_seat=st.selectbox("좌석",seats)
            def qr_bytes(s):
                link=urlunsplit((p.scheme,p.netloc,p.path,urlencode({"seat":s}),""))
                b=io.BytesIO();qrcode.make(link).save(b,format="PNG")
                return b.getvalue(),link
            image,link=qr_bytes(qr_seat)
            st.image(image,width=220,caption=f"공대 열람실 {qr_seat}")
            st.code(link,language=None)
            st.download_button("이 좌석 QR 다운로드",image,f"KHUR_{qr_seat}.png","image/png")
            if st.button("20개 좌석 QR ZIP 준비"):
                out=io.BytesIO()
                with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
                    for s in seats:z.writestr(f"KHUR_{s}.png",qr_bytes(s)[0])
                st.download_button("전체 QR ZIP 다운로드",out.getvalue(),"KHUR_QR_20.zip","application/zip")

if seat:
    st.subheader(f"공대 열람실 · {seat} 좌석")
    st.write("방금 스캔한 좌석입니다. 번호를 확인한 후 이용을 등록하세요.")
else:
    st.subheader("원하는 좌석의 QR을 스캔하세요")
    st.write("좌석 QR을 스캔하면 해당 좌석의 등록 화면으로 연결됩니다. 여기에서는 내 좌석 확인과 반납이 가능합니다.")

session=sb.auth.get_session()
if not session:
    st.info("좌석 등록에는 로그인이 필요합니다. 다른 좌석 QR을 스캔한 뒤 같은 계정으로 로그인하면 기존 좌석을 이어서 변경할 수 있습니다.")
    tabs=st.tabs(["로그인","회원가입"])
    with tabs[0]:
        with st.form("login"):
            email=st.text_input("이메일")
            password=st.text_input("비밀번호",type="password")
            submit=st.form_submit_button("로그인",use_container_width=True)
        if submit:
            try:
                sb.auth.sign_in_with_password({"email":email.strip(),"password":password})
                st.rerun()
            except Exception:
                st.error("로그인할 수 없습니다. 계정 정보와 이메일 인증 여부를 확인하세요.")
    with tabs[1]:
        st.caption("시연 시에는 Supabase에서 미리 생성한 테스트 계정을 사용하는 것이 편리합니다. 실제 학교 비밀번호를 입력하지 마세요.")
        with st.form("signup"):
            email_new=st.text_input("가입 이메일")
            pass_new=st.text_input("가입 비밀번호 (8자 이상)",type="password")
            submit_new=st.form_submit_button("계정 만들기")
        if submit_new:
            if len(pass_new)<8:
                st.error("비밀번호는 8자 이상 입력하세요.")
            else:
                try:
                    result=sb.auth.sign_up({"email":email_new.strip(),"password":pass_new})
                    if result.session:st.rerun()
                    st.success("가입 요청을 처리했습니다. 이메일 확인이 설정되어 있다면 메일에서 인증 후 로그인하세요.")
                except Exception:
                    st.error("가입 요청을 처리하지 못했습니다. 입력 정보와 인증 설정을 확인하세요.")
    st.stop()

st.caption(f"로그인 계정: {session.user.email}")
if st.button("로그아웃"):
    sb.auth.sign_out()
    st.rerun()
try:
    data=sb.rpc("khur_status",{}).execute().data
    mine=data.get("mine")
    occupied=set(data.get("occupied",[]))
except Exception:
    st.error("좌석 정보를 읽지 못했습니다. Supabase SQL 실행 여부와 설정을 확인하세요.")
    st.stop()
if "message" in st.session_state:st.success(st.session_state.pop("message"))
if mine:
    st.info(f"현재 내 좌석: {mine['seat_id']} · 종료 예정: {mine['ends_at']} (UTC)")
else:st.info("현재 이용 중인 좌석이 없습니다.")
if seat:
    if mine and mine['seat_id']==seat:
        st.success("이미 이용 중인 내 좌석입니다.")
    elif seat in occupied:
        st.warning("다른 이용자가 사용 중인 좌석입니다. 기존 내 좌석은 유지됩니다.")
    else:
        if mine:st.write(f"변경하면 {mine['seat_id']} 좌석은 자동 반납됩니다.")
        if st.button("이 좌석으로 변경하기" if mine else "이 좌석 이용하기",type="primary",use_container_width=True):
            try:
                result=sb.rpc("khur_book",{"p_seat":seat}).execute().data
                if result.get("ok"):
                    st.session_state.message=result["message"]
                    st.rerun()
                else:st.warning(result.get("message","등록하지 못했습니다."))
            except Exception:
                st.error("등록 요청을 처리하지 못했습니다. 새로고침 후 내 좌석을 먼저 확인하세요.")
if mine and st.button("내 좌석 반납하기",use_container_width=True):
    try:
        sb.rpc("khur_release",{}).execute()
        st.session_state.message="좌석을 반납했습니다."
        st.rerun()
    except Exception:st.error("반납하지 못했습니다. 내 좌석을 다시 확인하세요.")
if st.button("이용 정보 새로고침",use_container_width=True):st.rerun()
st.divider()
st.caption("이용 시간 2시간 · 한 계정당 한 좌석 · 현황은 새로고침 시 갱신됩니다. QR은 현장 방문을 증명하지 않습니다.")
st.caption("보안상 로그인은 현재 연결 세션에서만 유지됩니다. QR을 다시 열거나 새로고침하면 재로그인이 필요할 수 있지만 같은 계정의 좌석 기록은 유지됩니다.")
