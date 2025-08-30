import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

# --------------------------
# Database Connection
# --------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cursor = conn.cursor()

# --------------------------
# Helper Functions
# --------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()  # None if not found

def get_tasks(user_id=None):
    if user_id:
        cursor.execute("""
            SELECT task_id, title, description, due_date, status, priority, category, assigned_to
            FROM Tasks WHERE assigned_to=?
        """, (user_id,))
    else:
        cursor.execute("""
            SELECT task_id, title, description, due_date, status, priority, category, assigned_to
            FROM Tasks
        """)
    tasks = cursor.fetchall()
    # Convert timestamps to string up to seconds
    tasks_formatted = []
    for t in tasks:
        due = datetime.strptime(t[3], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        tasks_formatted.append((t[0], t[1], t[2], due, t[4], t[5], t[6], t[7]))
    return tasks_formatted

def add_task(title, description, due_date, priority, category, assigned_to):
    due_date_str = due_date.strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to)
        VALUES (?,?,?,?,?,?,?)
    """, (title, description, due_date_str, "Pending", priority, category, assigned_to))
    conn.commit()

def mark_task_complete(task_id):
    cursor.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
    conn.commit()

def add_comment(task_id, user_id, comment):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO Comments (task_id, user_id, comment, timestamp)
        VALUES (?,?,?,?)
    """, (task_id, user_id, comment, timestamp))
    conn.commit()

def get_comments(task_id):
    cursor.execute("""
        SELECT u.username, c.comment, c.timestamp
        FROM Comments c JOIN Users u ON c.user_id = u.user_id
        WHERE c.task_id=?
        ORDER BY c.timestamp DESC
    """, (task_id,))
    return cursor.fetchall()

# --------------------------
# Streamlit App
# --------------------------
st.set_page_config(page_title="Task Management System")
st.title("📋 Task Management System")

# --- Login ---
if "user" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Logged in as {user[1]} ({user[3]})")
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.experimental_rerun = None  # Not calling rerun; will reset on next run
        st.experimental_show("Logged out. Refresh the page.")

    menu = st.sidebar.selectbox("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Today", "➕ Create Task"])

    # --------------------------
    # View All Tasks
    # --------------------------
    if menu == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(None if user[3] in ["Admin", "Manager"] else user[0])
        if tasks:
            for t in tasks:
                with st.expander(f"{t[1]} (ID: {t[0]})"):
                    st.write(f"**Title:** {t[1]}")
                    st.write(f"**Description:** {t[2]}")
                    st.write(f"**Due Date:** {t[3]}")
                    st.write(f"**Status:** {t[4]}")
                    st.write(f"**Priority:** {t[5]}")
                    st.write(f"**Category:** {t[6]}")
                    st.write(f"**Assigned To (Employee ID):** {t[7]}")
                    if t[4] != "Completed" and t[7] == user[0]:
                        if st.button("Mark as Completed", key=f"complete_{t[0]}"):
                            mark_task_complete(t[0])
                            st.success("Task marked as Completed ✅")
        else:
            st.info("No tasks found.")

    # --------------------------
    # Overdue & Due Today
    # --------------------------
    elif menu == "⚠️ Overdue & Due Today":
        st.subheader("Overdue & Due Today Tasks")
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = datetime.now().replace(hour=23, minute=59, second=59)

        if user[3] in ["Admin", "Manager"]:
            cursor.execute("""
                SELECT task_id, title, due_date, status
                FROM Tasks
                WHERE (due_date < ? OR (due_date BETWEEN ? AND ?))
            """, (today_start.strftime("%Y-%m-%d %H:%M:%S"),
                  today_start.strftime("%Y-%m-%d %H:%M:%S"),
                  today_end.strftime("%Y-%m-%d %H:%M:%S")))
        else:
            cursor.execute("""
                SELECT task_id, title, due_date, status
                FROM Tasks
                WHERE assigned_to=? AND (due_date < ? OR (due_date BETWEEN ? AND ?))
            """, (user[0],
                  today_start.strftime("%Y-%m-%d %H:%M:%S"),
                  today_start.strftime("%Y-%m-%d %H:%M:%S"),
                  today_end.strftime("%Y-%m-%d %H:%M:%S")))
        tasks_due = cursor.fetchall()
        if tasks_due:
            df_due = pd.DataFrame(tasks_due, columns=["Task ID", "Title", "Due Date", "Status"])
            st.table(df_due)
        else:
            st.info("No overdue or due today tasks.")

    # --------------------------
    # Create Task
    # --------------------------
    elif menu == "➕ Create Task":
        if user[3] in ["Admin", "Manager"]:
            st.subheader("Create New Task")
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_datetime = datetime.combine(due_date, due_time)
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            assign_to = st.number_input("Assign to Employee ID", min_value=1, step=1)
            if st.button("Add Task"):
                add_task(title, description, due_datetime, priority, category, assign_to)
                st.success("Task created successfully!")
        else:
            st.info("You do not have permission to create tasks.")
