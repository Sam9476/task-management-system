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
    return result

def add_task(employee_id, title, description, due_datetime, priority, category, created_by):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category, created_by)
        VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?)
    """, (employee_id, title, description, due_datetime, priority, category, created_by))
    conn.commit()
    conn.close()

def get_tasks(role, employee_id, filter_status=None, search_keyword=None):
    conn = get_connection()
    cur = conn.cursor()
    query = "SELECT task_id, employee_id, title, description, due_datetime, status, priority, category FROM Tasks"
    params = []

    if role == "User":  # User can only see their own tasks
        query += " WHERE employee_id=?"
        params.append(employee_id)
    else:
        query += " WHERE 1=1"

    if filter_status:
        query += " AND status=?"
        params.append(filter_status)

    if search_keyword:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search_keyword}%", f"%{search_keyword}%"])

    cur.execute(query, params)
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
        menu.insert(0, "Add Task")

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

        # Filters
        filter_status = st.selectbox("Filter by Status", ["All", "Pending", "Completed"], index=0)
        search_keyword = st.text_input("🔍 Search by keyword")

        status_filter = None if filter_status == "All" else filter_status
        tasks = get_tasks(role, employee_id, filter_status=status_filter, search_keyword=search_keyword)

        if tasks:
            for t in tasks:
                task_id, emp_id, title, desc, due_dt, status, priority, category = t
                due_dt = datetime.strptime(due_dt, "%Y-%m-%d %H:%M:%S")

                # Highlight overdue and due in <24h
                if status == "Pending":
                    if due_dt < datetime.now():
                        status = "❌ Overdue"
                    elif due_dt < datetime.now() + timedelta(hours=24):
                        status = "⚠️ Due in <24h"

                with st.expander(f"📌 {title} (Assigned to: {emp_id})"):
                    st.write(f"**Description:** {desc}")
                    st.write(f"**Due:** {due_dt.strftime('%d-%m-%Y %H:%M')}")
                    st.write(f"**Priority:** {priority}")
                    st.write(f"**Category:** {category}")
                    st.write(f"**Status:** {status}")

                    if role in ["Admin", "Manager"] or emp_id == employee_id:
                        if st.button(f"Mark as Completed ✅ (Task {task_id})"):
                            update_task_status(task_id, "Completed")
                            st.success(f"Task {task_id} marked as Completed!")
                            st.rerun()
        else:
            st.info("No tasks found.")
