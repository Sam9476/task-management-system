import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# ========================
# DATABASE HELPERS
# ========================
def get_db():
    conn = sqlite3.connect("task_management.db", check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    # Users
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    );
    """)

    # Tasks
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        title TEXT,
        description TEXT,
        due_datetime DATETIME,
        status TEXT,
        priority TEXT,
        category TEXT,
        created_by INTEGER,
        FOREIGN KEY (employee_id) REFERENCES Users(employee_id),
        FOREIGN KEY (created_by) REFERENCES Users(employee_id)
    );
    """)

    # Comments
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Comments (
        comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        employee_id INTEGER,
        comment TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES Tasks(task_id),
        FOREIGN KEY (employee_id) REFERENCES Users(employee_id)
    );
    """)

    conn.commit()

def add_task(employee_id, title, description, due_datetime, priority, category, created_by):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category, created_by)
        VALUES (?,?,?,?,?,?,?,?)
    """, (employee_id, title, description, due_datetime, "Pending", priority, category, created_by))
    conn.commit()

def get_all_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT task_id, title, description, due_datetime, status, priority, category, employee_id
        FROM Tasks ORDER BY due_datetime ASC
    """)
    return cur.fetchall()

def get_overdue_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT task_id, title, description, due_datetime, status, priority, category, employee_id
        FROM Tasks
        WHERE status='Pending' AND due_datetime < ?
        ORDER BY due_datetime ASC
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))
    return cur.fetchall()

def get_due_soon_tasks():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT task_id, title, description, due_datetime, status, priority, category, employee_id
        FROM Tasks
        WHERE status='Pending' AND due_datetime BETWEEN ? AND ?
        ORDER BY due_datetime ASC
    """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
          (datetime.now() + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")))
    return cur.fetchall()

def add_comment(task_id, employee_id, comment):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO Comments (task_id, employee_id, comment) VALUES (?,?,?)",
                (task_id, employee_id, comment))
    conn.commit()

def get_comments(task_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT employee_id, comment, timestamp
        FROM Comments WHERE task_id=? ORDER BY timestamp DESC
    """, (task_id,))
    return cur.fetchall()

def validate_user(username, password):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT employee_id, role FROM Users WHERE username=? AND password=?",
                (username, password))
    return cur.fetchone()

# ========================
# STREAMLIT APP
# ========================
st.set_page_config(page_title="Task Management System", layout="wide")
init_db()

# Session state for login
if "user" not in st.session_state:
    st.session_state.user = None

# Login Page
if not st.session_state.user:
    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = validate_user(username, password)
        if user:
            st.session_state.user = {"employee_id": user[0], "role": user[1], "username": username}
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")

else:
    st.sidebar.title(f"Welcome, {st.session_state.user['username']} ({st.session_state.user['role']})")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.experimental_rerun()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # ========================
    # TAB 1: All Tasks
    # ========================
    with tab1:
        st.subheader("📋 All Tasks")
        tasks = get_all_tasks()
        for t in tasks:
            render_box = st.container(border=True)
            with render_box:
                st.write(f"**{t[1]}** | {t[6]} | Priority: {t[5]} | Status: {t[4]}")
                st.caption(f"Due: {t[3]} | Assigned To: {t[7]}")
                st.write(t[2])

                # Comments
                st.markdown("💬 **Comments**")
                comments = get_comments(t[0])
                for c in comments:
                    st.write(f"- [{c[2]}] User {c[0]}: {c[1]}")

                new_comment = st.text_input(f"Add comment for Task {t[0]}", key=f"c{t[0]}")
                if st.button(f"Add Comment {t[0]}", key=f"b{t[0]}"):
                    if new_comment.strip():
                        add_comment(t[0], st.session_state.user["employee_id"], new_comment)
                        st.experimental_rerun()

    # ========================
    # TAB 2: Overdue + Due Soon
    # ========================
    with tab2:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("⚠️ Overdue Tasks")
            for t in get_overdue_tasks():
                st.error(f"{t[1]} (Due: {t[3]}) | Assigned To: {t[7]}")

        with col2:
            st.subheader("⏳ Due in Next 24 Hours")
            for t in get_due_soon_tasks():
                st.warning(f"{t[1]} (Due: {t[3]}) | Assigned To: {t[7]}")

    # ========================
    # TAB 3: Create Task
    # ========================
    with tab3:
        if st.session_state.user["role"] in ["Admin", "Manager"]:
            st.subheader("➕ Create New Task")
            employee_id = st.number_input("Assign To (Employee ID)", min_value=1)
            title = st.text_input("Title")
            desc = st.text_area("Description")
            due_datetime = st.datetime_input("Due Date & Time")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.selectbox("Category", ["Work", "Personal", "Urgent", "Other"])

            if st.button("Create Task"):
                add_task(employee_id, title, desc,
                         due_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                         priority, category, st.session_state.user["employee_id"])
                st.success("Task created successfully ✅")
        else:
            st.warning("Only Admins and Managers can create tasks.")
