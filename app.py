import streamlit as st
import sqlite3
import datetime
import pandas as pd

# ---------- DATABASE FUNCTIONS ----------
def init_db():
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        due_date TEXT,
        status TEXT,
        priority TEXT,
        category TEXT,
        assigned_to INTEGER,
        FOREIGN KEY (assigned_to) REFERENCES Users(id)
    )
    """)
    conn.commit()
    conn.close()

def get_user(username, password):
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def get_tasks(user_id=None):
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    if user_id:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.id
            WHERE t.assigned_to=?
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.id
        """)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()
    conn.close()

def add_task(title, description, due_date, priority, category, assigned_to):
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to)
        VALUES (?, ?, ?, 'Pending', ?, ?, ?)
    """, (title, description, due_date, priority, category, assigned_to))
    conn.commit()
    conn.close()

def get_overdue_and_today_tasks(user_id=None):
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    today = datetime.date.today().strftime("%Y-%m-%d")

    if user_id:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.id
            WHERE date(t.due_date) < date(?)
            AND t.assigned_to=?
        """, (today, user_id))
        overdue = cursor.fetchall()

        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.id
            WHERE date(t.due_date) = date(?)
            AND t.assigned_to=?
        """, (today, user_id))
        today_tasks = cursor.fetchall()

    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.id
            WHERE date(t.due_date) < date(?)
        """, (today,))
        overdue = cursor.fetchall()

        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.id
            WHERE date(t.due_date) = date(?)
        """, (today,))
        today_tasks = cursor.fetchall()

    conn.close()
    return overdue, today_tasks

def get_users():
    conn = sqlite3.connect("task_management.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role FROM Users")
    users = cursor.fetchall()
    conn.close()
    return users

# ---------- APP UI ----------
st.set_page_config(page_title="📋 Task Management System", layout="wide")
init_db()

if "user" not in st.session_state:
    st.session_state.user = None

st.title("📋 Task Management System")

# ---------- LOGIN ----------
if not st.session_state.user:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = get_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Logged in as {user[1]} ({user[3]})")
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.title(f"Welcome, {user[1]} ({user[3]})")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Sidebar menu
    if user[3] in ["Admin", "Manager"]:
        menu = st.sidebar.radio("Menu", ["View Tasks", "Overdue Tasks", "Create Task"])
    else:
        menu = st.sidebar.radio("Menu", ["View My Tasks", "Overdue Tasks"])

    # View Tasks
    if menu in ["View Tasks", "View My Tasks"]:
        st.subheader("📌 Tasks")
        tasks = get_tasks(None if user[3] in ["Admin", "Manager"] else user[0])

        for task in tasks:
            with st.expander(f"{task[1]} (ID: {task[0]})"):
                st.write(f"**Title:** {task[1]}")
                st.write(f"**Description:** {task[2]}")
                st.write(f"**Due Date:** {task[3].split('.')[0]}")  # remove microseconds
                st.write(f"**Status:** {task[4]}")
                st.write(f"**Priority:** {task[5]}")
                st.write(f"**Category:** {task[6]}")
                st.write(f"**Assigned To:** {task[7]}")

                if task[4] != "Completed":
                    if st.button(f"Mark as Complete (ID {task[0]})", key=f"btn{task[0]}"):
                        update_task_status(task[0], "Completed")
                        st.success("Task marked as Completed ✅")
                        st.rerun()

    # Overdue & Today
    elif menu == "Overdue Tasks":
        st.subheader("⚠️ Overdue & Today's Tasks")
        overdue, today_tasks = get_overdue_and_today_tasks(None if user[3] in ["Admin", "Manager"] else user[0])

        if overdue:
            st.markdown("### ⏰ Overdue Tasks")
            df_overdue = pd.DataFrame(overdue, columns=["ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
            st.table(df_overdue)
        else:
            st.info("No overdue tasks 🎉")

        if today_tasks:
            st.markdown("### 📅 Tasks Due Today")
            df_today = pd.DataFrame(today_tasks, columns=["ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
            st.table(df_today)
        else:
            st.info("No tasks due today 🎉")

    # Create Task
    elif menu == "Create Task":
        st.subheader("➕ Create New Task")
        title = st.text_input("Title")
        description = st.text_area("Description")
        due_date = st.date_input("Due Date")
        due_time = st.time_input("Due Time")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        category = st.text_input("Category")

        # assign only to Users
        users = [u for u in get_users() if u[2] == "User"]
        assigned_to = st.selectbox("Assign To", users, format_func=lambda x: x[1]) if users else None

        if st.button("Create Task"):
            if assigned_to:
                due_datetime = datetime.datetime.combine(due_date, due_time).strftime("%Y-%m-%d %H:%M:%S")
                add_task(title, description, due_datetime, priority, category, assigned_to[0])
                st.success("✅ Task created successfully!")
                st.rerun()
            else:
                st.error("No users available to assign task.")
