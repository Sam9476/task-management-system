import streamlit as st
import sqlite3
from datetime import datetime, timedelta

DB = "task_management.db"

# ------------------ DB Helpers ------------------
def get_user(username, password):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT employee_id, role FROM Users WHERE username=? AND password=?", (username, password))
        return cur.fetchone()

def add_task(emp_id, title, desc, due, priority, category, created_by):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category, created_by)
            VALUES (?, ?, ?, ?, 'Pending', ?, ?, ?)
        """, (emp_id, title, desc, due, priority, category, created_by))
        conn.commit()

def get_tasks(emp_id=None, role=None):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        if role in ("Admin", "Manager"):
            cur.execute("SELECT task_id, employee_id, title, description, due_datetime, status, priority, category FROM Tasks")
        else:
            cur.execute("SELECT task_id, employee_id, title, description, due_datetime, status, priority, category FROM Tasks WHERE employee_id=?", (emp_id,))
        return cur.fetchall()

def get_overdue_tasks():
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT task_id, employee_id, title, due_datetime FROM Tasks WHERE status='Pending' AND due_datetime < ?", (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
        return cur.fetchall()

def get_due_24h_tasks():
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT task_id, employee_id, title, due_datetime FROM Tasks WHERE status='Pending' AND due_datetime BETWEEN ? AND ?", 
                    (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (datetime.now()+timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")))
        return cur.fetchall()

def add_comment(task_id, emp_id, comment):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO Comments (task_id, employee_id, comment) VALUES (?, ?, ?)", (task_id, emp_id, comment))
        conn.commit()

def get_comments(task_id):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT employee_id, comment, timestamp FROM Comments WHERE task_id=? ORDER BY timestamp DESC", (task_id,))
        return cur.fetchall()

# ------------------ Streamlit App ------------------
st.set_page_config(page_title="Task Management System", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user" not in st.session_state:
    st.session_state.user = None

# Login
if not st.session_state.logged_in:
    st.title("🔐 Login")
    u = st.text_input("Username")
    p = st.text_input("Password", type="password")
    if st.button("Login"):
        user = get_user(u, p)
        if user:
            st.session_state.logged_in = True
            st.session_state.user = {"id": user[0], "role": user[1], "username": u}
            st.rerun()
        else:
            st.error("Invalid credentials")

# Main App
else:
    st.sidebar.title(f"Welcome, {st.session_state.user['username']} ({st.session_state.user['role']})")
    choice = st.sidebar.radio("📌 Menu", ["Add Task", "View Tasks", "Overdue & Next 24h", "Logout"])

    # Add Task
    if choice == "Add Task":
        if st.session_state.user["role"] in ("Admin", "Manager"):
            st.header("➕ Add New Task")
            emp_id = st.number_input("Assign To (Employee ID)", min_value=1, step=1)
            title = st.text_input("Title")
            desc = st.text_area("Description")
            due = st.date_input("Due Date") 
            due_time = st.time_input("Due Time")
            due_dt = datetime.combine(due, due_time).strftime("%Y-%m-%d %H:%M:%S")
            priority = st.selectbox("Priority", ["Low","Medium","High"])
            category = st.selectbox("Category", ["Work","Meeting","Event","Other"])
            if st.button("Add Task"):
                add_task(emp_id, title, desc, due_dt, priority, category, st.session_state.user["id"])
                st.success("✅ Task added!")
        else:
            st.warning("🚫 Only Admin/Manager can add tasks.")

    # View Tasks
    elif choice == "View Tasks":
        st.header("📋 All Tasks")
        tasks = get_tasks(st.session_state.user["id"], st.session_state.user["role"])
        for t in tasks:
            st.subheader(f"🔹 {t[2]} (Task ID: {t[0]})")
            st.write(f"Assigned To: {t[1]} | Due: {t[4]} | Status: {t[5]} | Priority: {t[6]} | Category: {t[7]}")
            st.write(f"Description: {t[3]}")
            
            # Comments Section
            st.markdown("💬 **Comments**")
            comments = get_comments(t[0])
            for c in comments:
                st.write(f"- [{c[2]}] User {c[0]}: {c[1]}")
            new_comment = st.text_input(f"Add comment for Task {t[0]}", key=f"cmt_{t[0]}")
            if st.button(f"Post Comment {t[0]}"):
                if new_comment.strip():
                    add_comment(t[0], st.session_state.user["id"], new_comment)
                    st.success("Comment added!")
                    st.rerun()

    # Overdue & Due Soon
    elif choice == "Overdue & Next 24h":
        st.header("⏰ Task Deadlines")
        st.subheader("⚠️ Overdue Tasks")
        overdue = get_overdue_tasks()
        for o in overdue:
            st.write(f"Task {o[0]} | Employee {o[1]} | {o[2]} | Due {o[3]}")

        st.subheader("⏳ Due in Next 24 Hours")
        due24 = get_due_24h_tasks()
        for d in due24:
            st.write(f"Task {d[0]} | Employee {d[1]} | {d[2]} | Due {d[3]}")

    # Logout
    elif choice == "Logout":
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()
