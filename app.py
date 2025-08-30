import streamlit as st
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "task_management.db"

# -------------------- DATABASE UTILS --------------------
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def verify_user(username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT employee_id, role FROM Users WHERE username=? AND password=?", (username, password))
    result = cur.fetchone()
    conn.close()
    return result  # (employee_id, role) or None

def add_task(employee_id, title, description, due_datetime, priority, category, created_by):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category, created_by)
        VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?)
    """, (employee_id, title, description, due_datetime, priority, category, created_by))
    conn.commit()
    conn.close()

def get_tasks(role, employee_id):
    conn = get_connection()
    cur = conn.cursor()
    if role == "User":  # Users only see their own tasks
        cur.execute("SELECT task_id, title, description, due_datetime, status, priority, category FROM Tasks WHERE employee_id=?", (employee_id,))
    else:  # Admins & Managers see all tasks
        cur.execute("SELECT task_id, title, description, due_datetime, status, priority, category FROM Tasks")
    rows = cur.fetchall()
    conn.close()
    return rows

def update_task_status(task_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()
    conn.close()

# -------------------- STREAMLIT APP --------------------
st.set_page_config(page_title="Task Management System", layout="wide")

# Initialize session state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "employee_id" not in st.session_state:
    st.session_state.employee_id = None
if "role" not in st.session_state:
    st.session_state.role = None

# -------------------- LOGIN --------------------
if not st.session_state.logged_in:
    st.title("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        result = verify_user(username, password)
        if result:
            st.session_state.employee_id, st.session_state.role = result
            st.session_state.logged_in = True
            st.success(f"✅ Logged in as {username} ({st.session_state.role})")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

else:
    # -------------------- LOGOUT --------------------
    st.sidebar.title("⚙️ Menu")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.employee_id = None
        st.session_state.role = None
        st.rerun()

    role = st.session_state.role
    employee_id = st.session_state.employee_id

    # -------------------- MAIN DASHBOARD --------------------
    st.title("📋 Task Management Dashboard")

    menu = ["View Tasks"]
    if role in ["Admin", "Manager"]:
        menu.insert(0, "Add Task")  # only Admin/Manager can add tasks

    choice = st.sidebar.radio("Navigation", menu)

    # -------------------- ADD TASK --------------------
    if choice == "Add Task" and role in ["Admin", "Manager"]:
        st.subheader("➕ Add New Task")

        assign_to = st.number_input("Assign to Employee ID", min_value=1, step=1)
        title = st.text_input("Title")
        description = st.text_area("Description")
        due_date = st.date_input("Due Date")
        due_time = st.time_input("Due Time")
        due_datetime = datetime.combine(due_date, due_time).strftime("%Y-%m-%d %H:%M:%S")

        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        category = st.selectbox("Category", ["Development", "Reporting", "Maintenance", "Meetings", "Others"])

        if st.button("Add Task"):
            add_task(assign_to, title, description, due_datetime, priority, category, employee_id)
            st.success("✅ Task added successfully")

    # -------------------- VIEW TASKS --------------------
    elif choice == "View Tasks":
        st.subheader("📌 Task List")

        tasks = get_tasks(role, employee_id)

        if tasks:
            formatted = []
            for t in tasks:
                task_id, title, desc, due_dt, status, priority, category = t
                due_dt = datetime.strptime(due_dt, "%Y-%m-%d %H:%M:%S")

                # Status Check: overdue / due soon
                if status == "Pending":
                    if due_dt < datetime.now():
                        status = "❌ Overdue"
                    elif due_dt < datetime.now() + timedelta(hours=24):
                        status = "⚠️ Due in <24h"

                formatted.append([task_id, title, desc, due_dt.strftime("%d-%m-%Y %H:%M"), status, priority, category])

            st.table(formatted)
        else:
            st.info("No tasks available.")
