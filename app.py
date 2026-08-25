"""
HR Leave Request System
------------------------
Two logical sections in one app:
  1. Leave Request  -> for regular staff (Role = "User")
  2. HR-KMN          -> for the approver account (Role = "HR-KMN")

Which section a person sees is decided automatically by the Role stored
against their username in the Users sheet - there's nothing to pick.
"""
from datetime import date, timedelta

import pandas as pd
import streamlit as st

from auth_utils import authenticate, register_user
from config import (
    LEAVE_TYPES, ROLE_HR, ROLE_USER, STATUS_APPROVED, STATUS_PENDING_AO,
    STATUS_PENDING_HR, STATUS_REJECTED,
)
from email_utils import send_email
from gsheet_utils import append_request, get_requests_df, get_users_df, update_request_status

st.set_page_config(page_title="HR Leave Request", page_icon="🗓️", layout="centered")

# ---------------------------------------------------------------- styling --
st.markdown(
    """
    <style>
    div.block-container {padding-top: 1.5rem; max-width: 640px;}
    .stButton>button {width: 100%; height: 2.6em; font-weight: 600; border-radius: 8px;}
    div[data-testid="stForm"] {border: 1px solid #e6e6e6; padding: 1.2rem; border-radius: 12px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- session --
defaults = {"logged_in": False, "username": "", "role": "", "name": "", "empno": "",
            "designation": "", "email": ""}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)


def logout():
    for k, v in defaults.items():
        st.session_state[k] = v


# ============================================================== LOGIN =====
def render_login():
    st.title("🗓️ HR Leave Request")

    tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Log In")
        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
                return
            user = authenticate(username, password)
            if user is None:
                st.error("Invalid username or password.")
                return
            st.session_state.update(
                logged_in=True,
                username=user["Username"],
                role=user["Role"],
                name=user["Name"],
                empno=user["EmpNo"],
                designation=user["Designation"],
                email=user["Email"],
            )
            st.rerun()

    with tab_signup:
        st.caption("Create your account, then use it to log in on the other tab.")
        with st.form("signup_form", clear_on_submit=True):
            su_username = st.text_input("Choose a Username")
            su_password = st.text_input("Choose a Password", type="password")
            su_password2 = st.text_input("Confirm Password", type="password")
            su_empno = st.text_input("Emp No")
            su_name = st.text_input("Full Name")
            su_designation = st.text_input("Designation")
            su_email = st.text_input("Email")
            su_submitted = st.form_submit_button("Create Account")

        if su_submitted:
            if su_password != su_password2:
                st.error("Passwords do not match.")
            else:
                ok, message = register_user(
                    su_username, su_password, su_empno, su_name, su_designation, su_email
                )
                if ok:
                    st.success("Account created. Please switch to the Log In tab to sign in.")
                else:
                    st.error(message)


# ======================================================= LEAVE REQUEST ====
def render_leave_request_section():
    users_df = get_users_df()
    staff_df = users_df[users_df["Role"] == ROLE_USER].reset_index(drop=True)

    tab_new, tab_ao, tab_notify = st.tabs(["📝 New Request", "🧾 Acting Officer Approvals", "🔔 Notifications"])

    # ---- New Request tab -------------------------------------------------
    with tab_new:
        names = staff_df["Name"].tolist()
        default_idx = names.index(st.session_state.name) if st.session_state.name in names else 0

        with st.form("leave_request_form", clear_on_submit=True):
            selected_name = st.selectbox("Name", names, index=default_idx if names else 0)

            row = staff_df[staff_df["Name"] == selected_name].iloc[0] if names else None
            emp_no = row["EmpNo"] if row is not None else ""
            designation = row["Designation"] if row is not None else ""

            c1, c2 = st.columns(2)
            c1.text_input("Emp No", value=emp_no, disabled=True)
            c2.text_input("Designation", value=designation, disabled=True)

            acting_options = staff_df[staff_df["Name"] != selected_name]["Name"].tolist()
            acting_officer_name = st.selectbox("Acting Officer", acting_options) if acting_options else None

            leave_type = st.selectbox("Leave Type", LEAVE_TYPES)
            d1, d2 = st.columns(2)
            leave_date = d1.date_input("Leave Date", value=date.today(), min_value=date.today())
            return_date = d2.date_input("Return Date", value=date.today() + timedelta(days=1))
            reason = st.text_area("Reason", placeholder="Briefly explain the reason for leave")

            submitted = st.form_submit_button("Request")

        if submitted:
            if not acting_officer_name:
                st.error("There is no other staff member available to set as Acting Officer.")
            elif return_date < leave_date:
                st.error("Return Date cannot be earlier than Leave Date.")
            elif not reason.strip():
                st.error("Please enter a reason for the leave.")
            else:
                acting_row = staff_df[staff_df["Name"] == acting_officer_name].iloc[0]
                req_row = {
                    "Username": st.session_state.username,
                    "EmpNo": emp_no,
                    "Name": selected_name,
                    "Designation": designation,
                    "ActingOfficerUsername": acting_row["Username"],
                    "ActingOfficerName": acting_row["Name"],
                    "ActingOfficerEmail": acting_row["Email"],
                    "LeaveType": leave_type,
                    "LeaveDate": leave_date.strftime("%Y-%m-%d"),
                    "ReturnDate": return_date.strftime("%Y-%m-%d"),
                    "Reason": reason.strip(),
                }
                request_id = append_request(req_row)

                send_email(
                    acting_row["Email"],
                    f"Leave request awaiting your approval ({selected_name})",
                    f"Dear {acting_row['Name']},\n\n"
                    f"{selected_name} ({designation}) has applied for {leave_type} "
                    f"from {leave_date} to {return_date}, and has named you as Acting Officer "
                    f"during this period.\n\nReason: {reason.strip()}\n\n"
                    f"Please log in and approve or reject this request under "
                    f"Acting Officer Approvals.\n\nRequest ID: {request_id}",
                )
                st.success("✅ Request Sent to Acting Officer")
                st.rerun()

    # ---- Acting Officer Approvals tab -------------------------------------
    with tab_ao:
        render_acting_officer_approvals()

    # ---- Notifications tab -------------------------------------------------
    with tab_notify:
        render_user_notifications()


def render_acting_officer_approvals():
    requests_df = get_requests_df()
    username = st.session_state.username
    pending = requests_df[
        (requests_df["ActingOfficerUsername"] == username) & (requests_df["Status"] == STATUS_PENDING_AO)
    ].sort_values("RequestedOn", ascending=True) if not requests_df.empty else requests_df

    if pending.empty:
        st.info("No requests waiting for your approval.")
        return

    for _, r in pending.iterrows():
        with st.container(border=True):
            st.markdown(
                f"**{r['Name']}** · {r['Designation']}  \n"
                f"{r['LeaveType']}: {r['LeaveDate']} → {r['ReturnDate']}  \n"
                f"Reason: {r['Reason']}"
            )
            remarks = st.text_input("Remarks (optional)", key=f"ao_remarks_{r['RequestID']}")
            c1, c2 = st.columns(2)
            if c1.button("✅ Approve", key=f"ao_appr_{r['RequestID']}"):
                _ao_decide(r, approve=True, remarks=remarks)
            if c2.button("❌ Reject", key=f"ao_rej_{r['RequestID']}"):
                _ao_decide(r, approve=False, remarks=remarks)


def _ao_decide(request_row: pd.Series, approve: bool, remarks: str):
    if approve:
        new_status = STATUS_PENDING_HR
        update_request_status(request_row["RequestID"], new_status, remarks, stage="ao")
        users_df = get_users_df()
        for _, hr_user in users_df[users_df["Role"] == ROLE_HR].iterrows():
            send_email(
                hr_user["Email"],
                f"Leave request awaiting HR approval ({request_row['Name']})",
                f"Dear {hr_user['Name']},\n\n"
                f"{request_row['Name']} ({request_row['Designation']})'s {request_row['LeaveType']} request "
                f"({request_row['LeaveDate']} to {request_row['ReturnDate']}) has been approved by the "
                f"Acting Officer and now needs HR approval.\n\n"
                f"Request ID: {request_row['RequestID']}",
            )
        st.success("Approved and sent to HR.")
    else:
        new_status = STATUS_REJECTED
        update_request_status(request_row["RequestID"], new_status, remarks, stage="ao")
        users_df = get_users_df()
        requester = users_df[users_df["Username"] == request_row["Username"]]
        if not requester.empty:
            send_email(
                requester.iloc[0]["Email"],
                "Your leave request has been Rejected",
                f"Dear {request_row['Name']},\n\nYour {request_row['LeaveType']} request "
                f"({request_row['LeaveDate']} to {request_row['ReturnDate']}) was rejected by your "
                f"Acting Officer.\n" + (f"\nRemarks: {remarks}\n" if remarks else "")
                + "\nPlease check the Notifications section of the app for details.",
            )
        st.success("Request rejected.")
    st.rerun()


def render_user_notifications():
    requests_df = get_requests_df()
    if requests_df.empty:
        st.info("No notifications yet.")
        return

    username = st.session_state.username

    acting_for = requests_df[requests_df["ActingOfficerUsername"] == username].sort_values(
        "RequestedOn", ascending=False
    )
    own_updates = requests_df[
        (requests_df["Username"] == username)
        & (requests_df["Status"].isin([STATUS_APPROVED, STATUS_REJECTED]))
    ].sort_values("RequestedOn", ascending=False)
    own_pending = requests_df[
        (requests_df["Username"] == username)
        & (requests_df["Status"].isin([STATUS_PENDING_AO, STATUS_PENDING_HR]))
    ].sort_values("RequestedOn", ascending=False)

    if own_updates.empty and acting_for.empty and own_pending.empty:
        st.info("No notifications yet.")
        return

    for _, r in own_updates.iterrows():
        icon = "✅" if r["Status"] == STATUS_APPROVED else "❌"
        remarks = r["HRRemarks"] or r["AORemarks"]
        st.container(border=True).markdown(
            f"{icon} **Your {r['LeaveType']} request was {r['Status']}**  \n"
            f"{r['LeaveDate']} → {r['ReturnDate']}"
            + (f"  \n_Remarks: {remarks}_" if remarks else "")
        )

    for _, r in own_pending.iterrows():
        waiting_on = "Acting Officer" if r["Status"] == STATUS_PENDING_AO else "HR"
        st.container(border=True).markdown(
            f"⏳ **{r['LeaveType']} request pending {waiting_on} approval**  \n"
            f"{r['LeaveDate']} → {r['ReturnDate']}  \nActing Officer: {r['ActingOfficerName']}"
        )

    for _, r in acting_for.iterrows():
        st.container(border=True).markdown(
            f"👤 **You are Acting Officer for {r['Name']}**  \n"
            f"{r['LeaveType']}: {r['LeaveDate']} → {r['ReturnDate']}  \nStatus: {r['Status']}"
        )


# ============================================================= HR-KMN =====
def render_hr_section():
    tab_pending, tab_all = st.tabs(["✅ Pending Approvals", "📋 All Requests"])

    with tab_pending:
        requests_df = get_requests_df()
        pending = requests_df[requests_df["Status"] == STATUS_PENDING_HR].sort_values(
            "RequestedOn", ascending=True
        )
        if pending.empty:
            st.info("No pending requests.")
        for _, r in pending.iterrows():
            with st.container(border=True):
                st.markdown(
                    f"**{r['Name']}** · {r['Designation']}  \n"
                    f"{r['LeaveType']}: {r['LeaveDate']} → {r['ReturnDate']}  \n"
                    f"Acting Officer: {r['ActingOfficerName']} (approved)  \n"
                    f"Reason: {r['Reason']}"
                )
                remarks = st.text_input("Remarks (optional)", key=f"remarks_{r['RequestID']}")
                c1, c2 = st.columns(2)
                if c1.button("✅ Approve", key=f"appr_{r['RequestID']}"):
                    _decide(r, STATUS_APPROVED, remarks)
                if c2.button("❌ Reject", key=f"rej_{r['RequestID']}"):
                    _decide(r, STATUS_REJECTED, remarks)

    with tab_all:
        requests_df = get_requests_df()
        if requests_df.empty:
            st.info("No requests yet.")
            return
        status_filter = st.selectbox(
            "Filter by status",
            ["All", STATUS_PENDING_AO, STATUS_PENDING_HR, STATUS_APPROVED, STATUS_REJECTED],
        )
        view = requests_df if status_filter == "All" else requests_df[requests_df["Status"] == status_filter]
        st.dataframe(
            view[["Name", "LeaveType", "LeaveDate", "ReturnDate", "ActingOfficerName", "Status", "RequestedOn"]],
            use_container_width=True,
            hide_index=True,
        )


def _decide(request_row: pd.Series, status: str, remarks: str):
    update_request_status(request_row["RequestID"], status, remarks, stage="hr")
    users_df = get_users_df()
    requester = users_df[users_df["Username"] == request_row["Username"]]
    if not requester.empty:
        send_email(
            requester.iloc[0]["Email"],
            f"Your leave request has been {status}",
            f"Dear {request_row['Name']},\n\nYour {request_row['LeaveType']} request "
            f"({request_row['LeaveDate']} to {request_row['ReturnDate']}) has been {status} by HR.\n"
            + (f"\nHR remarks: {remarks}\n" if remarks else "")
            + "\nPlease check the Notifications section of the app for details.",
        )
    st.success(f"Request {status.lower()}.")
    st.rerun()


# ================================================================ MAIN =====
def render_header():
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"**{st.session_state.name}**  \n{st.session_state.designation} · {st.session_state.role}")
    if c2.button("Log Out"):
        logout()
        st.rerun()
    st.divider()


def main():
    if not st.session_state.logged_in:
        render_login()
        return

    render_header()
    if st.session_state.role == ROLE_HR:
        render_hr_section()
    else:
        render_leave_request_section()


if __name__ == "__main__":
    main()
