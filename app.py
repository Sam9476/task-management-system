import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time

# --------------------------
# Database Connection
# --------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cursor = conn.cursor()

# --------------------------
# Custom Styling (CSS)
# --------------------------
st.markdown("""
    <style>
    /* Main page background */
    .stApp {
        background: linear-gradient(135deg, #f0f4f8, #d9e2ec);
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #1e3a8a; /* deep blue */
        font-family: 'Segoe UI', sans-serif;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #1e293b;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    /* Tables */
    .dataframe {
        border-collapse: collapse;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.1);
    }
    .dataframe th {
        background: #1e3a8a;
        color: white !important;
        text-align: center;
        padding: 8px;
    }
    .dataframe td {
        padding: 8px;
        text-align: center;
        background: #f9fafb;
    }

    /* Success & Error boxes */
    .stSuccess {
        background-color: #dcfce7 !important;
        color: #166534 !important;
        border-radius: 10px;
    }
    .stError {
        background-color: #fee2e2 !important;
        color: #991b1b !important;
        border-radius: 10px;
    }

    /* Buttons */
    button {
        border-radius: 8px !important;
        padding: 0.6em 1.2em;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------
# Helper Functions
# --------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def get_tasks(user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, 
                   t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.user_id
        """)
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status, 
                   t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.user_id
            WHERE t.assigned_to = ?
        """, (user[0],))
    return cursor.fetchall()

def add_task(creator, title, description, due_date, priority, category, assign_to):
    if creator[3] in ["Admin", "Manager"]:
        cursor.execute("""
            INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to, created_by)
            VALUES (?,?,?,?,?,?,?,?)
        """, (title, description, due_date, "Pending", priority, category, assign_to, creator[0]))
        conn.commit()
        return True
    return False

def mark_task_complete(task_id, user):
    cursor.execute("SELECT assigned_to FROM Tasks WHERE task_id=?", (task_id,))
    result = cursor.fetchone()
    if result and user[0] == result[0]:
        cursor.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
        conn.commit()
        return True
    return False

def delete_task(task_id, user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("SELECT * FROM Tasks WHERE task_id=?", (task_id,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM Tasks WHERE task_id=?", (task_id,))
            conn.commit()
            return True
    return False

def get_overdue_and_today_tasks(user):
    today = datetime.today().date()
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date < ? AND t.status='Pending'
        """, (today,))
        overdue = cursor.fetchall()
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date = ? AND t.status='Pending'
        """, (today,))
        today_tasks = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date < ? AND t.status='Pending' AND t.assigned_to=?
        """, (today, user[0]))
        overdue = cursor.fetchall()
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date = ? AND t.status='Pending' AND t.assigned_to=?
        """, (today, user[0]))
        today_tasks = cursor.fetchall()
    return overdue, today_tasks

# --------------------------
# Streamlit App
# --------------------------
st.title("📋 Task Management System")

# --- Login ---
if "user" not in st.session_state:
    st.subheader("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"✅ Logged in as {user[1]} ({user[3]})")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.header("📌 Navigation")
    st.sidebar.write(f"👤 {user[1]} ({user[3]})")
    menu = st.sidebar.radio("Go to", ["View Tasks", "Overdue & Today Tasks", "Create Task", "Logout"])

    # Logout
    if menu == "Logout":
        st.session_state.clear()
        st.success("✅ You have been logged out.")
        st.rerun()

    # View Tasks
    elif menu == "View Tasks":
        st.subheader("📋 All Tasks")
        tasks = get_tasks(user)
        if tasks:
            df = pd.DataFrame(tasks, columns=[
                "Task ID", "Title", "Description", "Due Date", 
                "Status", "Priority", "Category", "Assigned To"
            ])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("ℹ️ No tasks found.")

        # Mark complete (for users)
        if user[3] not in ["Admin", "Manager"] and tasks:
            st.subheader("✅ Mark Task as Completed")
            task_id_to_complete = st.number_input("Enter Task ID", min_value=1, step=1)
            if st.button("Mark as Complete"):
                if mark_task_complete(task_id_to_complete, user):
                    st.success(f"Task {task_id_to_complete} completed 🎉")
                    time.sleep(1.2)
                    st.rerun()
                else:
                    st.error("❌ Not authorized or task not found.")

        # Delete task (for Admin/Manager)
        if user[3] in ["Admin", "Manager"] and tasks:
            st.subheader("🗑️ Delete Task")
            task_id_to_delete = st.number_input("Enter Task ID to delete", min_value=1, step=1, key="delete")
            if st.button("Delete Task"):
                if delete_task(task_id_to_delete, user):
                    st.success(f"🗑️ Task {task_id_to_delete} deleted successfully!")
                    time.sleep(1.2)
                    st.rerun()
                else:
                    st.error("❌ Task not found.")

    # Overdue & Today Tasks
    elif menu == "Overdue & Today Tasks":
        st.subheader("⚠️ Deadlines Overview")
        overdue, today_tasks = get_overdue_and_today_tasks(user)
        st.markdown("### 🔴 Overdue Tasks")
        if overdue:
            df_overdue = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
            st.dataframe(df_overdue, use_container_width=True)
        else:
            st.success("🎉 No overdue tasks!")

        st.markdown("### 🟡 Tasks Due Today")
        if today_tasks:
            df_today = pd.DataFrame(today_tasks, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
            st.dataframe(df_today, use_container_width=True)
        else:
            st.info("No tasks due today.")

    # Create Task
    elif menu == "Create Task":
        st.subheader("➕ Create New Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Time")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            due_datetime = datetime.combine(due_date, due_time)

            cursor.execute("SELECT user_id, username FROM Users WHERE user_id != ?", (user[0],))
            users_list = cursor.fetchall()
            if users_list:
                assign_to_name = st.selectbox("Assign To", [u[1] for u in users_list])
                assign_to = [u[0] for u in users_list if u[1] == assign_to_name][0]

                if st.button("Add Task"):
                    if add_task(user, title, description, due_datetime, priority, category, assign_to):
                        st.success("✅ Task created successfully!")
                        time.sleep(1.2)
                        st.rerun()
                    else:
                        st.error("❌ Not authorized.")
            else:
                st.warning("No users available to assign.")
        else:
            st.info("Only Admin/Manager can create tasks.")
