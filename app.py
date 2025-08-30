import streamlit as st
import sqlite3
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
    user = cursor.fetchone()
    if user:
        return {"employee_id": user[0], "username": user[1], "role": user[3]}
    return None

def get_all_tasks():
    cursor.execute("SELECT task_id, title, description, due_datetime, status, priority, category, employee_id FROM Tasks ORDER BY due_datetime ASC")
    return cursor.fetchall()

def get_tasks_by_employee(emp_id):
    cursor.execute("SELECT task_id, title, description, due_datetime, status, priority, category, employee_id FROM Tasks WHERE employee_id=? ORDER BY due_datetime ASC", (emp_id,))
    return cursor.fetchall()

def add_task(employee_id, title, description, due_datetime, priority, category):
    cursor.execute("""
        INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (employee_id, title, description, due_datetime, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def get_comments(task_id):
    cursor.execute("""
        SELECT employee_id, comment, timestamp 
        FROM Comments 
        WHERE task_id=? 
        ORDER BY timestamp DESC
    """, (task_id,))
    return cursor.fetchall()

def add_comment(task_id, employee_id, comment):
    cursor.execute("INSERT INTO Comments (task_id, employee_id, comment) VALUES (?, ?, ?)", (task_id, employee_id, comment))
    conn.commit()

# ---------------------------
# Streamlit App
# ---------------------------
st.title("📋 Task Management System")

# ---------------------------
# Login / Logout
# ---------------------------
if "user" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Logged in as {user['username']} ({user['role']})")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user['username']} ({user['role']})")
    menu = st.sidebar.selectbox("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.experimental_rerun()

    # ---------------------------
    # VIEW TASKS
    # ---------------------------
    if menu == "📋 All Tasks":
        st.subheader("📋 All Tasks")

        tasks = get_all_tasks() if user["role"] in ["Admin","Manager"] else get_tasks_by_employee(user["employee_id"])

        if tasks:
            for t in tasks:
                with st.expander(f"{t[1]} (ID: {t[0]})"):
                    st.markdown(f"**Title:** {t[1]}")
                    st.markdown(f"**Description:** {t[2]}")
                    st.markdown(f"**Due Date & Time:** {t[3]}")
                    st.markdown(f"**Status:** {t[4]}")
                    st.markdown(f"**Priority:** {t[5]}")
                    st.markdown(f"**Category:** {t[6]}")
                    st.markdown(f"**Assigned To (Employee ID):** {t[7]}")

                    # Task completion for assigned user
                    if t[7] == user["employee_id"] and t[4] != "Completed":
                        if st.button("Mark as Completed ✅", key=f"complete_{t[0]}", type="primary"):
                            update_task_status(t[0], "Completed")
                            st.success("Task marked as Completed ✅")
                            st.experimental_rerun()

                    # Comments
                    st.markdown("💬 **Comments**")
                    comments = get_comments(t[0])
                    if comments:
                        for c in comments:
                            st.write(f"- [{c[2]}] Employee {c[0]}: {c[1]}")
                    else:
                        st.info("No comments yet.")

                    # Add comment
                    new_comment = st.text_input(f"Add comment for Task {t[0]}", key=f"c{t[0]}")
                    if st.button(f"Add Comment", key=f"b{t[0]}"):
                        if new_comment.strip():
                            add_comment(t[0], user["employee_id"], new_comment)
                            st.success("Comment added ✅")
                            st.experimental_rerun()

    # ---------------------------
    # OVERDUE & DUE SOON
    # ---------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        st.subheader("⚠️ Overdue & Due Soon")

        now = datetime.now()
        next_24hr = now + timedelta(hours=24)

        # Due in next 24 hours
        st.markdown("**Tasks Due in Next 24 Hours**")
        cursor.execute("""
            SELECT task_id, title, due_datetime, status FROM Tasks
            WHERE due_datetime BETWEEN ? AND ? AND status='Pending'
            ORDER BY due_datetime ASC
        """, (now, next_24hr))
        tasks_24hr = cursor.fetchall()
        if tasks_24hr:
            st.table(tasks_24hr)
        else:
            st.info("No tasks due in next 24 hours.")

        # Overdue
        st.markdown("**Overdue Tasks**")
        cursor.execute("""
            SELECT task_id, title, due_datetime, status FROM Tasks
            WHERE due_datetime < ? AND status='Pending'
            ORDER BY due_datetime ASC
        """, (now,))
        overdue_tasks = cursor.fetchall()
        if overdue_tasks:
            st.table(overdue_tasks)
        else:
            st.info("No overdue tasks.")

    # ---------------------------
    # CREATE TASK
    # ---------------------------
    elif menu == "➕ Create Task":
        st.subheader("➕ Create Task")
        if user["role"] in ["Admin","Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_full = datetime.combine(due_date, due_time)
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            employee_id = st.number_input("Assign to Employee ID", min_value=1, step=1)

            if st.button("Add Task"):
                add_task(employee_id, title, description, due_full, priority, category)
                st.success("Task added successfully ✅")
        else:
            st.info("Only Admin or Manager can create tasks.")
