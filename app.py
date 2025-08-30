import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_FILE = "task_management.db"

# ---------- DB FUNCTIONS ----------
def get_user(username, password):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

def get_tasks(user_id=None, role=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    if role in ["Admin", "Manager"]:
        cursor.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks""")
    else:
        cursor.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks WHERE assigned_to=?""", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def update_task_status(task_id, status):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()
    conn.close()

def get_comments(task_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""SELECT U.username, C.comment, C.timestamp 
                      FROM Comments C JOIN Users U ON C.employee_id=U.user_id 
                      WHERE task_id=? ORDER BY timestamp DESC""", (task_id,))
    comments = cursor.fetchall()
    conn.close()
    return comments

def add_comment(task_id, employee_id, comment):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Comments (task_id, employee_id, comment, timestamp) VALUES (?, ?, ?, ?)",
                   (task_id, employee_id, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def create_task(title, description, due_date, priority, category, assigned_to):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to) 
                      VALUES (?, ?, ?, 'Pending', ?, ?, ?)""",
                   (title, description, due_date, priority, category, assigned_to))
    conn.commit()
    conn.close()

def get_users():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username FROM Users")
    users = cursor.fetchall()
    conn.close()
    return users

# ---------- STREAMLIT APP ----------
st.set_page_config(page_title="📋 Task Management System", layout="wide")
st.title("📋 Task Management System")

# LOGIN SYSTEM
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = get_user(username, password)
        if user:
            st.session_state.user = user
            st.rerun()
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.success(f"Logged in as {user[1]} ({user[3]})")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    # Sidebar Navigation
    menu = st.sidebar.radio("Menu", ["View Tasks", "Overdue Tasks", "Create Task" if user[3] in ["Admin","Manager"] else "View Tasks"])

    # View Tasks Tab
    if menu == "View Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(user[0], user[3])
        for t in tasks:
            with st.expander(f"{t[1]} (ID: {t[0]})"):
                st.write(f"**Description:** {t[2]}")
                st.write(f"**Due Date:** {t[3]}")
                st.write(f"**Status:** {t[4]}")
                st.write(f"**Priority:** {t[5]}")
                st.write(f"**Category:** {t[6]}")
                st.write(f"**Assigned To (ID):** {t[7]}")

                if t[4] != "Completed" and st.button("✅ Mark as Complete", key=f"complete{t[0]}"):
                    update_task_status(t[0], "Completed")
                    st.success("Task marked as Completed ✅")
                    st.rerun()

                st.markdown("**💬 Comments**")
                for c in get_comments(t[0]):
                    st.write(f"- {c[0]}: {c[1]} ({c[2]})")

                new_comment = st.text_input("Add a comment:", key=f"comment{t[0]}")
                if st.button("Submit Comment", key=f"submit{t[0]}"):
                    if new_comment.strip():
                        add_comment(t[0], user[0], new_comment)
                        st.rerun()

    # Overdue & Due Today
    elif menu == "Overdue Tasks":
        st.subheader("Overdue & Due Today Tasks")

        tasks = get_tasks(user[0], user[3])
        df = pd.DataFrame(tasks, columns=["ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
        df["Due Date"] = pd.to_datetime(df["Due Date"])

        overdue = df[df["Due Date"] < datetime.now()]
        today = df[df["Due Date"].dt.date == datetime.now().date()]

        if not overdue.empty:
            st.markdown("### ⏰ Overdue Tasks")
            st.dataframe(overdue.drop(columns=["Assigned To"]).reset_index(drop=True))

        if not today.empty:
            st.markdown("### 📅 Tasks Due Today")
            st.dataframe(today.drop(columns=["Assigned To"]).reset_index(drop=True))

    # Create Task (Admin/Manager only)
    elif menu == "Create Task":
        st.subheader("➕ Create New Task")
        title = st.text_input("Title")
        description = st.text_area("Description")
        due_date = st.text_input("Due Date (YYYY-MM-DD HH:MM:SS)")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        category = st.text_input("Category")
        users = get_users()
        user_map = {name: uid for uid, name in users}
        assigned_to = st.selectbox("Assign To", list(user_map.keys()))

        if st.button("Create Task"):
            if title and description and due_date and category:
                create_task(title, description, due_date, priority, category, user_map[assigned_to])
                st.success("✅ Task created successfully!")
                st.rerun()
            else:
                st.error("Please fill all fields.")
