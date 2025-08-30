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
        # Return as dict
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
    cursor.execute("SELECT employee_id, comment, timestamp FROM Comments WHERE task_id=? ORDER BY timestamp DESC", (task_id,))
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
            task_titles = [f"{t[1]} (ID: {t[0]})" for t in tasks]
            selected_task_title = st.selectbox("Select a Task to View Details", task_titles)
            selected_task = tasks[task_titles.index(selected_task_title)]

            st.markdown(f"**Title:** {selected_task[1]}")
            st.markdown(f"**Description:** {selected_task[2]}")
            st.markdown(f"**Due Date & Time:** {selected_task[3]}")
            st.markdown(f"**Status:** {selected_task[4]}")
            st.markdown(f"**Priority:** {selected_task[5]}")
            st.markdown(f"**Category:** {selected_task[6]}")
            st.markdown(f"**Assigned To (Employee ID):** {selected_task[7]}")

            # Task completion for assigned user
            if selected_task[7] == user["employee_id"] and selected_task[4] != "Completed":
                if st.button("Mark as Completed"):
                    update_task_status(selected_task[0], "Completed")
                    st.success("Task marked as Completed ✅")
                    st.experimental_rerun()

            # Comments
            st.markdown("💬 **Comments**")
            comments = get_comments(selected_task[0])
            if comments:
                for c in comments:
                    st.write(f"- [{c[2]}] Employee {c[0]}: {c[1]}")
            else:
                st.info("No comments yet.")

            # Add comment
            new_comment = st.text_input(f"Add comment for Task {selected_task[0]}", key=f"c{selected_task[0]}")
            if st.button(f"Add Comment {selected_task[0]}", key=f"b{selected_task[0]}"):
                if new_comment.strip():
                    add_comment(selected_task[0], user["employee_id"], new_comment)
                    st.success("Comment added ✅")
                    st.experimental_rerun()
        else:
            st.info("No tasks found.")

    # ---------------------------
    # OVERDUE & DUE SOON
    # ---------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        st.subheader("⚠️ Overdue & Due Soon")

        today = datetime.now()
        next_day = today + timedelta(days=1)
        next_3_days = today + timedelta(days=3)

        # Due in next 24 hours
        st.markdown("**Tasks Due in Next 24 Hours**")
        cursor.execute("""
            SELECT task_id, title, due_datetime, status FROM Tasks
            WHERE due_datetime BETWEEN ? AND ? AND status='Pending'
            ORDER BY due_datetime ASC
        """, (today, next_day))
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
        """, (today,))
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
            due_datetime = st.date_input("Due Date") 
            due_time = st.time_input("Due Time")
            due_full = datetime.combine(due_datetime, due_time)
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            employee_id = st.number_input("Assign to Employee ID", min_value=1, step=1)

            if st.button("Add Task"):
                add_task(employee_id, title, description, due_full, priority, category)
                st.success("Task added successfully ✅")
        else:
            st.info("Only Admin or Manager can create tasks.")
