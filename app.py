import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

# --------------------------
# Database Connection
# --------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cursor = conn.cursor()

# --------------------------
# Session State Trigger
# --------------------------
if "refresh" not in st.session_state:
    st.session_state["refresh"] = False

# --------------------------
# Helper Functions
# --------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()  # None if not found

def get_tasks(user_id=None):
    if user_id:
        cursor.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to 
                          FROM Tasks WHERE assigned_to=?""", (user_id,))
    else:
        cursor.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to 
                          FROM Tasks""")
    return cursor.fetchall()

def add_task(title, description, due_date, priority, category, assigned_to):
    cursor.execute("""INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to)
                      VALUES (?, ?, ?, 'Pending', ?, ?, ?)""",
                   (title, description, due_date, priority, category, assigned_to))
    conn.commit()

def mark_task_complete(task_id):
    cursor.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
    conn.commit()

def get_overdue_tasks(user_id=None):
    today = datetime.today().date()
    if user_id:
        cursor.execute("""SELECT task_id, title, due_date, status FROM Tasks 
                          WHERE assigned_to=? AND due_date < ? AND status='Pending'""",
                       (user_id, today))
    else:
        cursor.execute("""SELECT task_id, title, due_date, status FROM Tasks 
                          WHERE due_date < ? AND status='Pending'""", (today,))
    return cursor.fetchall()

def get_due_today_tasks(user_id=None):
    today = datetime.today().date()
    if user_id:
        cursor.execute("""SELECT task_id, title, due_date, status FROM Tasks 
                          WHERE assigned_to=? AND due_date = ? AND status='Pending'""",
                       (user_id, today))
    else:
        cursor.execute("""SELECT task_id, title, due_date, status FROM Tasks 
                          WHERE due_date = ? AND status='Pending'""", (today,))
    return cursor.fetchall()

# --------------------------
# Streamlit App
# --------------------------
st.title("📋 Task Management System")

# --- Login ---
if "user" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.success(f"Logged in as {user[1]} ({user[3]})")
            st.session_state.user = user
            st.session_state.refresh = not st.session_state.refresh  # trigger rerun
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")
    
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.session_state.refresh = not st.session_state.refresh  # trigger rerun

    menu = st.sidebar.selectbox("Menu", ["View Tasks", "Overdue & Due Today Tasks", "Create Task"])

    # --------------------------
    # View Tasks
    # --------------------------
    if menu == "View Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(None if user[3] in ["Admin", "Manager"] else user[0])
        if tasks:
            df = pd.DataFrame(tasks, columns=["Task ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
            st.table(df)
        else:
            st.info("No tasks found.")

    # --------------------------
    # Overdue & Due Today Tasks
    # --------------------------
    elif menu == "Overdue & Due Today Tasks":
        st.subheader("Overdue Tasks")
        overdue = get_overdue_tasks(None if user[3] in ["Admin", "Manager"] else user[0])
        if overdue:
            df_overdue = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status"])
            st.table(df_overdue)
        else:
            st.info("No overdue tasks.")

        st.subheader("Tasks Due Today")
        due_today = get_due_today_tasks(None if user[3] in ["Admin", "Manager"] else user[0])
        if due_today:
            df_today = pd.DataFrame(due_today, columns=["Task ID", "Title", "Due Date", "Status"])
            st.table(df_today)
        else:
            st.info("No tasks due today.")

    # --------------------------
    # Create Task
    # --------------------------
    elif menu == "Create Task":
        st.subheader("Create Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            # Assigned to select
            cursor.execute("SELECT user_id, username FROM Users")
            users = cursor.fetchall()
            assign_to_dict = {f"{u[1]} (ID: {u[0]})": u[0] for u in users}
            assigned_to = st.selectbox("Assign Task To", list(assign_to_dict.keys()))
            assigned_to_id = assign_to_dict[assigned_to]
            if st.button("Add Task"):
                add_task(title, description, due_date, priority, category, assigned_to_id)
                st.success("Task added successfully!")
        else:
            st.info("You do not have authority to create tasks.")
