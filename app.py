import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# --------------------------
# Database Connection
# --------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cur = conn.cursor()

# --------------------------
# Helper Functions
# --------------------------
def login_user(username, password):
    cur.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    user = cur.fetchone()
    return user

def get_tasks_for_user(user):
    if user[3] in ["Admin","Manager"]:
        cur.execute("SELECT * FROM Tasks")
    else:
        cur.execute("SELECT * FROM Tasks WHERE employee_id=?", (user[0],))
    return cur.fetchall()

def add_task(employee_id, title, description, due_datetime, priority, category):
    cur.execute("""
        INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category)
        VALUES (?,?,?,?,?,?,?)
    """, (employee_id, title, description, due_datetime, "Pending", priority, category))
    conn.commit()

def mark_task_completed(task_id):
    cur.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
    conn.commit()

def add_comment(task_id, employee_id, comment):
    cur.execute("""
        INSERT INTO Comments (task_id, employee_id, comment)
        VALUES (?,?,?)
    """, (task_id, employee_id, comment))
    conn.commit()

def get_comments(task_id):
    cur.execute("""
        SELECT employee_id, comment, timestamp FROM Comments
        WHERE task_id=? ORDER BY timestamp DESC
    """, (task_id,))
    return cur.fetchall()

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
            st.session_state.user = user
            st.success(f"Logged in as {user[1]} ({user[3]})")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")

    # --- Logout ---
    if st.sidebar.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.stop()

    # Sidebar menu
    menu = st.sidebar.radio("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # --------------------------
    # VIEW TASKS
    # --------------------------
    if menu == "📋 All Tasks":
        tasks = get_tasks_for_user(user)
        if tasks:
            for t in tasks:
                with st.expander(f"{t[2]} (ID: {t[0]}) - {t[5]}"):
                    st.write(f"**Title:** {t[2]}")
                    st.write(f"**Description:** {t[3]}")
                    st.write(f"**Due Date & Time:** {t[4]}")
                    st.write(f"**Status:** {t[5]}")
                    st.write(f"**Priority:** {t[6]}")
                    st.write(f"**Category:** {t[7]}")
                    st.write(f"**Assigned To (Employee ID):** {t[1]}")

                    # Mark as completed if task assigned to current user
                    if user[0] == t[1] and t[5] != "Completed":
                        if st.button("Mark as Completed ✅", key=f"complete_{t[0]}"):
                            mark_task_completed(t[0])
                            st.success("Task marked as Completed ✅")
                            st.experimental_rerun()

                    # Comments
                    st.write("**Comments:**")
                    comments = get_comments(t[0])
                    for c in comments:
                        st.write(f"Employee {c[0]} ({c[2]}): {c[1]}")

                    new_comment = st.text_input("Add Comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}"):
                        if new_comment.strip():
                            add_comment(t[0], user[0], new_comment)
                            st.success("Comment added!")
                            st.experimental_rerun()
        else:
            st.info("No tasks available.")

    # --------------------------
    # OVERDUE & DUE SOON
    # --------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        now = datetime.now()
        next24h = now + timedelta(hours=24)

        st.subheader("Overdue Tasks")
        cur.execute("SELECT * FROM Tasks WHERE status='Pending' AND due_datetime < ?", (now.strftime("%Y-%m-%d %H:%M:%S"),))
        overdue_tasks = cur.fetchall()
        if overdue_tasks:
            for t in overdue_tasks:
                st.write(f"{t[2]} (ID: {t[0]}) - Due: {t[4]} - Priority: {t[6]}")
        else:
            st.info("No overdue tasks.")

        st.subheader("Tasks Due in Next 24 Hours")
        cur.execute("""
            SELECT * FROM Tasks WHERE status='Pending'
            AND due_datetime BETWEEN ? AND ?
        """, (now.strftime("%Y-%m-%d %H:%M:%S"), next24h.strftime("%Y-%m-%d %H:%M:%S")))
        due_soon = cur.fetchall()
        if due_soon:
            for t in due_soon:
                st.write(f"{t[2]} (ID: {t[0]}) - Due: {t[4]} - Priority: {t[6]}")
        else:
            st.info("No tasks due in next 24 hours.")

    # --------------------------
    # CREATE TASK
    # --------------------------
    elif menu == "➕ Create Task":
        if user[3] in ["Admin","Manager"]:
            st.subheader("Create Task")
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_datetime = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_dt = datetime.combine(due_datetime, due_time).strftime("%Y-%m-%d %H:%M:%S")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.selectbox("Category", ["General","Reporting","Meeting","Analytics"])
            assign_to = st.number_input("Assign to Employee ID", min_value=1, step=1)

            if st.button("Add Task"):
                add_task(assign_to, title, description, due_dt, priority, category)
                st.success("Task added successfully!")
        else:
            st.info("Only Admin or Manager can create tasks.")
