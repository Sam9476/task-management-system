import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------
# Database Connection
# ---------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cursor = conn.cursor()

# ---------------------------
# Helper Functions
# ---------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def get_tasks_for_user(user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("SELECT * FROM Tasks")
    else:
        cursor.execute("SELECT * FROM Tasks WHERE assigned_to=?", (user[0],))
    return cursor.fetchall()

def add_task(title, description, due_date, priority, category, assigned_to, created_by):
    cursor.execute("""
        INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to, created_by)
        VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?)
    """, (title, description, due_date, priority, category, assigned_to, created_by))
    conn.commit()

def mark_task_complete(task_id):
    cursor.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
    conn.commit()

def get_comments(task_id):
    cursor.execute("SELECT c.comment, u.username, c.timestamp FROM Comments c JOIN Users u ON c.employee_id=u.employee_id WHERE c.task_id=? ORDER BY c.timestamp DESC", (task_id,))
    return cursor.fetchall()

def add_comment(task_id, employee_id, comment):
    cursor.execute("INSERT INTO Comments (task_id, employee_id, comment, timestamp) VALUES (?, ?, ?, ?)",
                   (task_id, employee_id, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()

# ---------------------------
# Streamlit App
# ---------------------------
st.title("📋 Task Management System")

if "user" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.experimental_rerun()  # <-- will fix below

    menu = st.sidebar.radio("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # ---------------------------
    # All Tasks
    # ---------------------------
    if menu == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks_for_user(user)
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

                    # Show comments
                    st.write("**Comments:**")
                    comments = get_comments(t[0])
                    for c in comments:
                        st.write(f"{c[1]} ({c[2]}): {c[0]}")

                    # Add comment
                    comment_text = st.text_area("Add Comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}"):
                        if comment_text.strip() != "":
                            add_comment(t[0], user[0], comment_text)
                            st.success("Comment added!")

    # ---------------------------
    # Overdue & Due Soon
    # ---------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        st.subheader("Tasks Due Today / Overdue")
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=0)
        next24h = now + timedelta(hours=24)

        # Overdue
        if user[3] in ["Admin", "Manager"]:
            cursor.execute("SELECT * FROM Tasks WHERE status='Pending' AND due_date<?", (now.strftime("%Y-%m-%d %H:%M:%S"),))
        else:
            cursor.execute("SELECT * FROM Tasks WHERE status='Pending' AND due_date<? AND assigned_to=?", (now.strftime("%Y-%m-%d %H:%M:%S"), user[0]))
        overdue_tasks = cursor.fetchall()
        if overdue_tasks:
            st.write("**Overdue Tasks:**")
            for t in overdue_tasks:
                st.write(f"{t[1]} (ID: {t[0]}) - Due: {t[3]} - Assigned To: {t[7]}")

        # Due Today
        if user[3] in ["Admin", "Manager"]:
            cursor.execute("SELECT * FROM Tasks WHERE status='Pending' AND due_date BETWEEN ? AND ?", (today_start.strftime("%Y-%m-%d %H:%M:%S"), today_end.strftime("%Y-%m-%d %H:%M:%S")))
        else:
            cursor.execute("SELECT * FROM Tasks WHERE status='Pending' AND due_date BETWEEN ? AND ? AND assigned_to=?", (today_start.strftime("%Y-%m-%d %H:%M:%S"), today_end.strftime("%Y-%m-%d %H:%M:%S"), user[0]))
        today_tasks = cursor.fetchall()
        if today_tasks:
            st.write("**Tasks Due Today:**")
            for t in today_tasks:
                st.write(f"{t[1]} (ID: {t[0]}) - Due: {t[3]} - Assigned To: {t[7]}")

    # ---------------------------
    # Create Task
    # ---------------------------
    elif menu == "➕ Create Task":
        if user[3] not in ["Admin", "Manager"]:
            st.info("Only Admin or Manager can create tasks.")
        else:
            st.subheader("Create Task")
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_datetime = datetime.combine(due_date, due_time)
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            assigned_to = st.number_input("Assign To (Employee ID)", min_value=1, step=1)
            if st.button("Add Task"):
                add_task(title, description, due_datetime.strftime("%Y-%m-%d %H:%M:%S"), priority, category, assigned_to, user[0])
                st.success("Task added successfully!")
