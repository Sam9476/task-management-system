import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import pandas as pd

# ----------------- Database Setup -----------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cursor = conn.cursor()

# Get username by user_id
def get_username(user_id):
    cursor.execute("SELECT username FROM Users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    return result[0] if result else "Unknown"

# Get tasks with proper filtering
def get_tasks(user_id=None, role=None):
    if role in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT task_id, title, description, due_date, status, priority, category, assigned_to 
            FROM Tasks
        """)
    else:
        cursor.execute("""
            SELECT task_id, title, description, due_date, status, priority, category, assigned_to 
            FROM Tasks WHERE assigned_to=?
        """, (user_id,))
    return cursor.fetchall()

# Update task status
def update_task_status(task_id, status):
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

# Create new task
def create_task(title, description, due_date, priority, category, assigned_to):
    cursor.execute("""
        INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (title, description, due_date, "Pending", priority, category, assigned_to))
    conn.commit()

# ----------------- Streamlit App -----------------
st.title("🗂️ Task Management System")

# Session state login setup
if "user" not in st.session_state:
    st.session_state.user = None

# Login Page
if not st.session_state.user:
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()
        if user:
            st.session_state.user = user
            st.success(f"Welcome {username}!")
            st.rerun()
        else:
            st.error("Invalid username or password")

# After Login
else:
    user = st.session_state.user
    st.sidebar.subheader("📌 Menu")
    menu = ["View Tasks", "Overdue & Due Today Tasks"]
    if user[3] in ["Admin", "Manager"]:
        menu.append("Create Task")
    menu.append("Logout")

    choice = st.sidebar.radio("Select Option", menu)

    # View Tasks
    if choice == "View Tasks":
        st.subheader("📋 All Tasks")
        tasks = get_tasks(user_id=user[0], role=user[3])
        if tasks:
            for t in tasks:
                with st.expander(f"🔹 {t[1]} (Assigned to: {get_username(t[7])})"):
                    st.write(f"**Description:** {t[2]}")
                    st.write(f"**Due Date:** {t[3]}")
                    st.write(f"**Status:** {t[4]}")
                    st.write(f"**Priority:** {t[5]}")
                    st.write(f"**Category:** {t[6]}")
                    if user[3] == "User" and t[7] == user[0] and t[4] != "Completed":
                        if st.button(f"Mark as Complete (Task {t[0]})"):
                            update_task_status(t[0], "Completed")
                            st.success("✅ Task marked as completed!")
                            st.rerun()
        else:
            st.info("No tasks assigned.")

    # Overdue & Due Today Tasks
    elif choice == "Overdue & Due Today Tasks":
        st.subheader("⏳ Overdue & Due Today Tasks")
        tasks = get_tasks(user_id=user[0], role=user[3])
        today = datetime.now().date()

        overdue = [t for t in tasks if datetime.strptime(t[3], "%Y-%m-%d %H:%M:%S").date() < today and t[4] != "Completed"]
        due_today = [t for t in tasks if datetime.strptime(t[3], "%Y-%m-%d %H:%M:%S").date() == today and t[4] != "Completed"]

        # Overdue Tasks
        if overdue:
            st.write("### ❌ Overdue Tasks")
            df_overdue = pd.DataFrame(overdue, columns=["ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
            df_overdue["Assigned To"] = df_overdue["Assigned To"].apply(get_username)
            df_overdue["Due Date"] = pd.to_datetime(df_overdue["Due Date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            st.table(df_overdue.drop(columns=["ID"]))
        else:
            st.info("✅ No overdue tasks.")

        # Due Today Tasks
        if due_today:
            st.write("### 📅 Tasks Due Today")
            df_today = pd.DataFrame(due_today, columns=["ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
            df_today["Assigned To"] = df_today["Assigned To"].apply(get_username)
            df_today["Due Date"] = pd.to_datetime(df_today["Due Date"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            st.table(df_today.drop(columns=["ID"]))
        else:
            st.info("✅ No tasks due today.")

    # Create Task (only Admin/Manager)
    elif choice == "Create Task":
        st.subheader("🆕 Create Task")
        title = st.text_input("Task Title")
        description = st.text_area("Task Description")
        due_date = st.date_input("Due Date")
        time_input = st.time_input("Due Time")
        due_datetime = datetime.combine(due_date, time_input)

        priority = st.selectbox("Priority", ["Low", "Medium", "High"])
        category = st.text_input("Category")

        cursor.execute("SELECT user_id, username FROM Users WHERE role='User'")
        users = cursor.fetchall()
        assigned_to = st.selectbox("Assign To", users, format_func=lambda x: x[1])

        if st.button("Create Task"):
            create_task(title, description, due_datetime.strftime("%Y-%m-%d %H:%M:%S"), priority, category, assigned_to[0])
            st.success("✅ Task Created Successfully!")

    # Logout
    elif choice == "Logout":
        del st.session_state["user"]
        st.success("You have been logged out.")
        st.rerun()
