import io
import zipfile
from urllib.parse import urlsplit, urlunsplit, urlencode
import streamlit as st
import qrcode
from supabase import create_client

st.set_page_config(page_title="KHUR · 좌석 QR 등록",page_icon="📚",layout="centered")
st.markdown("""
<style>
:root{--wine:#93152a;--deep:#651021;--cream:#faf7f2;--ink:#302429;--muted:#8b797c;--line:#eadfda}
.stApp{background:var(--cream);color:var(--ink)}
.block-container{max-width:640px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3{color:var(--deep)!important;letter-spacing:-.045em}
p,label,button{letter-spacing:-.025em}
[data-testid="stHeader"]{background:rgba(250,247,242,.93)}
[data-testid="stForm"]{background:#fffdfb;border:1px solid var(--line);border-radius:22px;padding:24px}
[data-testid="stTextInput"] input{border-radius:12px;background:#fffdfb;min-height:46px}
.stButton>button,.stDownloadButton>button,[data-testid="stFormSubmitButton"] button{border-radius:14px;min-height:48px;border:1px solid #dfceca;font-weight:650;background:#fffdfb;color:var(--deep)}
.stButton>button[kind="primary"],[data-testid="stFormSubmitButton"] button{background:var(--wine);color:white;border-color:var(--wine)}
.stButton>button:hover,.stDownloadButton>button:hover{border-color:var(--wine);color:var(--wine)}
.stButton>button[kind="primary"]:hover,[data-testid="stFormSubmitButton"] button:hover{background:var(--deep);color:white;border-color:var(--deep)}
[data-testid="stExpander"]{background:#fffdfb;border:1px solid var(--line);border-radius:16px}
[data-testid="stAlert"]{border-radius:16px}
[data-baseweb="tab-list"]{gap:20px;border-bottom:1px solid var(--line)}
[data-baseweb="tab"]{color:var(--muted);padding:10px 4px}
[data-baseweb="tab"][aria-selected="true"]{color:var(--wine);font-weight:750}
[data-baseweb="tab-highlight"]{background:var(--wine)}
.brand-head{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--line);padding-bottom:18px;margin-bottom:30px}
.wordmark{font-size:33px;font-weight:900;letter-spacing:-2px;color:var(--wine);line-height:1}
.wordmark small{display:block;letter-spacing:2px;font-size:8px;font-weight:600;margin-top:7px}
.brand-pill{font-size:11px;border:1px solid #dfc8c7;border-radius:30px;padding:7px 11px;color:var(--wine)}
.hero{margin:0 0 26px}.eyebrow{font-size:10px;letter-spacing:2px;font-weight:750;color:var(--wine);margin-bottom:10px}
.hero h1{font-size:31px!important;line-height:1.35;font-weight:750;padding:0;margin:0 0 12px}
.hero p{font-size:13px;line-height:1.8;color:var(--muted);margin:0}
.seat-card{background:#fffdfb;border:1px solid var(--line);border-radius:24px;overflow:hidden;margin:20px 0 22px;box-shadow:0 8px 28px #65102107}
.seat-top{display:flex;align-items:center;justify-content:space-between;padding:16px 22px;border-bottom:1px solid var(--line);font-size:11px;color:var(--muted)}
.seat-tag{color:var(--wine);font-size:10px;font-weight:700;letter-spacing:1px}
.seat-main{padding:25px 24px 22px;display:flex;gap:20px;align-items:center}
.seat-icon{width:60px;height:68px;border-radius:17px;background:var(--wine);display:flex;align-items:center;justify-content:center;color:#fff;font-size:32px}
.seat-number{font-size:46px;font-weight:850;letter-spacing:-2px;line-height:1;color:var(--deep)}
.seat-sub{font-size:12px;color:var(--muted);margin-top:9px}
.seat-bottom{background:#f5eeea;padding:13px 22px;font-size:11px;color:#80676b;line-height:1.7}
.brand-foot{border-top:1px solid var(--line);margin-top:28px;padding-top:18px;display:flex;justify-content:space-between;color:var(--muted);font-size:10px;line-height:1.8}
@media(max-width:480px){.block-container{padding:1.3rem 1.1rem 2rem}.hero h1{font-size:27px!important}.seat-number{font-size:42px}[data-testid="stForm"]{padding:18px}}
</style>
<div class="brand-head"><div class="wordmark">KHUR<small>YOUR SEAT. YOUR FOCUS.</small></div><div class="brand-pill">공대 열람실</div></div>
<div class="hero"><div class="eyebrow">KYUNG HEE · READING ROOM</div><h1>좋은 자리가<br>좋은 하루를 만든다.</h1><p>마음에 드는 자리에서 QR을 스캔하세요.<br>자리 등록부터 변경까지, 그 자리에서 간편하게.</p></div>
""",unsafe_allow_html=True)
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


if seat:
    st.markdown(f"""<div class="seat-card"><div class="seat-top"><span>공과대학 열람실</span><span class="seat-tag">SCANNED SEAT</span></div><div class="seat-main"><div class="seat-icon">▤</div><div><div class="seat-number">{seat}</div><div class="seat-sub">방금 스캔한 좌석</div></div></div><div class="seat-bottom">좌석 번호를 확인해주세요. 로그인 후 이용 가능 여부를 확인하고 등록할 수 있습니다.</div></div>""",unsafe_allow_html=True)
else:
    st.markdown("""<div class="seat-card"><div class="seat-top"><span>좌석 이용 안내</span><span class="seat-tag">SCAN &amp; SIT</span></div><div class="seat-main"><div class="seat-icon">⌗</div><div><div style="font-size:21px;font-weight:750;color:#651021">내 자리는 QR로 간편하게</div><div class="seat-sub">이용할 좌석에 부착된 QR을 스캔하세요.</div></div></div><div class="seat-bottom">01 QR 스캔 &nbsp; → &nbsp; 02 로그인 &nbsp; → &nbsp; 03 좌석 등록<br>이미 이용 중이라면 로그인 후 내 좌석을 확인하거나 반납할 수 있습니다.</div></div>""",unsafe_allow_html=True)

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

st.caption("두리서 · 경진대회 시제품 / 학교 공식 서비스가 아닙니다.")

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

st.markdown('<div class="brand-foot"><span>KHUR · 두리서<br>YOUR SEAT. YOUR FOCUS.</span><span>공대 열람실<br>QR 기반 좌석 등록·변경</span></div>',unsafe_allow_html=True)
