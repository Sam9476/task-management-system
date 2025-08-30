import streamlit as st
import sqlite3
from datetime import datetime, timedelta

DB_NAME = "task_management.db"

# DB connection
def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

# Login
def login_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user

# Fetch tasks
def get_tasks(user_id=None, role="User"):
    conn = get_connection()
    cursor = conn.cursor()
    if role in ["Admin", "Manager"]:
        cursor.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks""")
    else:
        cursor.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to 
                          FROM Tasks WHERE assigned_to=?""", (user_id,))
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# Update status
def update_task_status(task_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()
    conn.close()

# Comments
def get_comments(task_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT employee_id, comment, timestamp FROM Comments WHERE task_id=? ORDER BY timestamp DESC", (task_id,))
    comments = cursor.fetchall()
    conn.close()
    return comments

def add_comment(task_id, employee_id, comment):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Comments (task_id, employee_id, comment, timestamp) VALUES (?, ?, ?, ?)",
                   (task_id, employee_id, comment, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

# ---- Streamlit UI ----
st.set_page_config(page_title="Task Management System", layout="wide")
st.title("📋 Task Management System")

if "user" not in st.session_state:
    st.session_state.user = None

# Login
if not st.session_state.user:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Logged in as {user[1]} ({user[3]})")
            st.rerun()
        else:
            st.error("Invalid username or password")
else:
    user = st.session_state.user
    st.sidebar.write(f"👤 Logged in as **{user[1]}** ({user[3]})")
    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.rerun()

    tab1, tab2 = st.tabs(["All Tasks", "Overdue & Due Soon Tasks"])

    # ---- All Tasks ----
    with tab1:
        st.subheader("📋 All Tasks")
        tasks = get_tasks(user_id=user[0], role=user[3])
        for task in tasks:
            with st.expander(f"{task[1]} (ID: {task[0]})"):
                st.write(f"**Title:** {task[1]}")
                st.write(f"**Description:** {task[2]}")
                st.write(f"**Due Date & Time:** {task[3]}")
                st.write(f"**Status:** {task[4]}")
                st.write(f"**Priority:** {task[5]}")
                st.write(f"**Category:** {task[6]}")
                st.write(f"**Assigned To (Employee ID):** {task[7]}")

                # Mark as complete
                if task[4] != "Completed" and user[0] == task[7]:
                    if st.button("✅ Mark as Complete", key=f"complete_{task[0]}"):
                        update_task_status(task[0], "Completed")
                        st.success("Task marked as Completed ✅")
                        st.rerun()

                # Comments
                st.write("### 💬 Comments")
                comments = get_comments(task[0])
                for c in comments:
                    st.write(f"- User {c[0]}: {c[1]} ({c[2]})")

                new_comment = st.text_input("Add a comment", key=f"comment_{task[0]}")
                if st.button("Post Comment", key=f"post_{task[0]}"):
                    add_comment(task[0], user[0], new_comment)
                    st.rerun()

    # ---- Overdue & Due Soon ----
    with tab2:
        st.subheader("⏰ Overdue & Due Soon Tasks (Today / Next 3 Days)")
        tasks = get_tasks(user_id=user[0], role=user[3])
        now = datetime.now()
        upcoming = now + timedelta(days=3)
        for task in tasks:
            due_date = datetime.strptime(task[3], "%Y-%m-%d %H:%M:%S")
            if due_date < now or due_date <= upcoming:
                with st.expander(f"{task[1]} (ID: {task[0]})"):
                    st.write(f"**Title:** {task[1]}")
                    st.write(f"**Description:** {task[2]}")
                    st.write(f"**Due Date & Time:** {due_date.strftime('%Y-%m-%d %H:%M:%S')}")
                    st.write(f"**Status:** {task[4]}")
                    st.write(f"**Priority:** {task[5]}")
                    st.write(f"**Category:** {task[6]}")
                    st.write(f"**Assigned To (Employee ID):** {task[7]}")
