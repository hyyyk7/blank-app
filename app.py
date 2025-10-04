# save as app.py
import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

DATA_FILE = "planner_data.json"

# ---------------------------
# Helpers: load / save data
# ---------------------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    # default structure
    return {
        "profile": {
            "income": 0,
            "fixed_expenses": 0,
            "saving_invest": 0,
            "emergency": 0,
            "saving_pct": None,
            "invest_pct": None,
            "emergency_pct": None
        },
        "wishlist": [],  # list of items: {id,name,target,months,current,priority,created}
        "transactions": []  # optional: track manual deposits/expenses
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def new_item_id(data):
    existing = [it.get("id", 0) for it in data["wishlist"]]
    return max(existing)+1 if existing else 1

# ---------------------------
# Core calculations
# ---------------------------
def calculate_usable(profile):
    income = profile["income"]
    fixed = profile["fixed_expenses"]
    saving = profile["saving_invest"]
    emergency = profile["emergency"]
    usable = income - (fixed + saving + emergency)
    return max(0, usable)

def monthly_need_for_item(item):
    months = item.get("months", 1) or 1
    need = (item["target"] - item.get("current", 0)) / months
    return max(0, int(need))

def allocate_to_wishlist(usable, wishlist):
    # simple priority allocation: sort by priority asc (1 highest)
    alloc = []
    remaining = usable
    sorted_items = sorted(wishlist, key=lambda x: x.get("priority", 999))
    for it in sorted_items:
        need = monthly_need_for_item(it)
        assigned = min(need, remaining)
        alloc.append({"id": it["id"], "name": it["name"], "assigned": int(assigned), "need": int(need)})
        remaining -= assigned
        if remaining <= 0:
            break
    return alloc, remaining

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="사고싶은 물건 저축 플래너", layout="wide")
st.title("💸 사고싶은 물건 저축 플래너 (Streamlit MVP)")

data = load_data()
profile = data["profile"]

# --- 왼쪽: 프로필 / 예산 설정 ---
with st.sidebar:
    st.header("프로필 / 월 예산 설정")
    income = st.number_input("월 수입 (원)", min_value=0, value=int(profile.get("income", 0)))
    fixed_expenses = st.number_input("월 고정 지출 (원) (예: 구독료 등)", min_value=0, value=int(profile.get("fixed_expenses", 0)))
    saving_invest = st.number_input("저축/투자 금액 (원)", min_value=0, value=int(profile.get("saving_invest", 0)))
    emergency = st.number_input("비상금 (원)", min_value=0, value=int(profile.get("emergency", 0)))

    # Quick-recommend buttons
    st.markdown("**추천 버튼**")
    if st.button("추천: 저축55만원(군적금 예시)"):
        saving_invest = 550000
    if st.button("추천 비율 (예: 30% 저축 / 3% 비상)"):
        saving_invest = int(income * 0.30)
        emergency = int(income * 0.03)

    if st.button("저장 (프로필)"):
        profile.update({
            "income": int(income),
            "fixed_expenses": int(fixed_expenses),
            "saving_invest": int(saving_invest),
            "emergency": int(emergency)
        })
        data["profile"] = profile
        save_data(data)
        st.success("프로필 저장됨")

# Main area
st.subheader("이번 달 요약")
profile = data["profile"]
usable = calculate_usable(profile)
col1, col2, col3 = st.columns([1,1,1])
col1.metric("월 수입", f"{profile.get('income',0):,}원")
col2.metric("고정 지출", f"{profile.get('fixed_expenses',0):,}원")
col3.metric("저축/투자", f"{profile.get('saving_invest',0):,}원")
col1.metric("비상금", f"{profile.get('emergency',0):,}원")
col2.metric("가용 자금", f"{usable:,}원")

# Wishlist management
st.markdown("---")
st.header("사고 싶은 물건 (Wishlist)")

# Add item form
with st.expander("새 물건 추가"):
    with st.form("add_item"):
        name = st.text_input("물건 이름")
        target = st.number_input("목표 금액 (원)", min_value=0, value=200000)
        months = st.number_input("목표 기간 (개월)", min_value=1, value=4)
        priority = st.selectbox("우선순위 (1:높음)", [1,2,3,4,5], index=2)
        submitted = st.form_submit_button("추가")
        if submitted:
            new_id = new_item_id(data)
            item = {
                "id": new_id,
                "name": name,
                "target": int(target),
                "months": int(months),
                "current": 0,
                "priority": int(priority),
                "created": datetime.now().isoformat()
            }
            data["wishlist"].append(item)
            save_data(data)
            st.success(f"'{name}' 추가됨")

# Show wishlist table
if data["wishlist"]:
    df = pd.DataFrame(data["wishlist"])
    df_display = df[["id","name","target","months","current","priority","created"]].copy()
    df_display["달성률(%)"] = (df_display["current"] / df_display["target"]).fillna(0).apply(lambda x: round(x*100,1))
    st.dataframe(df_display.sort_values(by="priority"))
else:
    st.info("등록된 물건이 없습니다. '새 물건 추가'로 시작하세요.")

# Allocation preview
st.markdown("---")
st.header("자동 배분(미리보기)")
alloc, rem_after_alloc = allocate_to_wishlist(usable, data["wishlist"])
if alloc:
    alloc_df = pd.DataFrame(alloc)
    st.table(alloc_df.assign(need=lambda d: d["need"].map("{:,}".format),
                              assigned=lambda d: d["assigned"].map("{:,}".format)))
    st.write(f"모든 할당 후 남는 생활비: {rem_after_alloc:,}원")
else:
    st.info("할당할 목표가 없습니다. 목표를 추가해보세요.")
    st.write(f"가용 자금(전액 생활비 가능): {usable:,}원")

# Allow user to "apply" this month's allocation (move assigned amounts to current of items)
st.markdown("---")
st.header("이번 달 저축 반영")
if alloc:
    if st.button("이번 달 할당 적용하기 (현재 적립액에 반영)"):
        id_to_assigned = {a["id"]: a["assigned"] for a in alloc}
        for it in data["wishlist"]:
            add_amt = id_to_assigned.get(it["id"], 0)
            if add_amt > 0:
                it["current"] = it.get("current", 0) + int(add_amt)
        # record transaction
        data["transactions"].append({
            "ts": datetime.now().isoformat(),
            "type": "monthly_alloc",
            "detail": {"alloc": alloc},
        })
        save_data(data)
        st.success("이번 달 할당이 반영되었습니다.")
else:
    st.info("적용 가능한 할당이 없습니다.")

# Manual transaction (deposit to a wishlist item)
st.markdown("---")
st.header("수동 입금 / 거래 기록")
with st.form("txn_form"):
    if data["wishlist"]:
        choices = {f"{it['id']}: {it['name']}": it["id"] for it in data["wishlist"]}
        sel = st.selectbox("대상 물건", list(choices.keys()))
        amount = st.number_input("금액 (원)", min_value=0, value=0)
        memo = st.text_input("메모 (선택)")
        ok = st.form_submit_button("입금/기록")
        if ok:
            target_id = choices[sel]
            for it in data["wishlist"]:
                if it["id"] == target_id:
                    it["current"] = it.get("current", 0) + int(amount)
                    break
            data["transactions"].append({
                "ts": datetime.now().isoformat(),
                "type": "manual_deposit",
                "amount": int(amount),
                "item_id": target_id,
                "memo": memo
            })
            save_data(data)
            st.success("입금(기록) 완료")
    else:
        st.info("먼저 물건을 추가하세요.")

# Progress visualization
st.markdown("---")
st.header("진행률 & 리포트")
if data["wishlist"]:
    for it in sorted(data["wishlist"], key=lambda x: x.get("priority", 999)):
        name = it["name"]
        target = it["target"]
        current = it.get("current", 0)
        pct = min(1.0, current/target) if target>0 else 0
        col_a, col_b = st.columns([3,1])
        with col_a:
            st.write(f"**{name}** — {current:,}/{target:,}원 ({pct*100:.1f}%)")
            st.progress(pct)
        with col_b:
            if current >= target:
                st.success("🎉 달성!")
            else:
                est_months_remaining = (target - current) / (monthly_need_for_item(it) or 1)
                st.write(f"예상 남은 개월: {est_months_remaining:.1f}")

# Transactions table
st.markdown("---")
st.header("거래 내역 (최근)")
if data["transactions"]:
    txn_df = pd.DataFrame(data["transactions"])[-20:][::-1]
    st.dataframe(txn_df)
else:
    st.info("거래 내역이 없습니다.")

# Footer: reset / export
st.markdown("---")
st.write("⚙️ 데이터 내보내기 / 초기화")
col1, col2 = st.columns(2)
with col1:
    if st.button("데이터 내보내기(JSON)"):
        st.download_button("다운로드 (planner_data.json)", json.dumps(data, ensure_ascii=False, indent=2), file_name="planner_data.json", mime="application/json")
with col2:
    if st.button("데이터 초기화(모두 삭제)"):
        if st.confirm("정말로 모든 데이터를 초기화하시겠어요?"):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            data = load_data()
            st.experimental_rerun()

st.caption("로컬 파일(planner_data.json)에 데이터가 저장됩니다. 공유/백업 원하면 '데이터 내보내기' 사용하세요.")