import streamlit as st
import sqlite3
from datetime import datetime, timedelta

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
    return cursor.fetchone()

def get_tasks(user_id=None):
    if user_id:
        cursor.execute("""
            SELECT task_id, title, description, due_date, status, priority, category, assigned_to 
            FROM Tasks WHERE assigned_to=? OR created_by=?""", (user_id, user_id))
    else:
        cursor.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks")
    return cursor.fetchall()

def add_task(assigned_to, created_by, title, description, due_date, priority, category):
    cursor.execute("""
        INSERT INTO Tasks (assigned_to, created_by, title, description, due_date, status, priority, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (assigned_to, created_by, title, description, due_date, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def add_comment(task_id, user_id, comment):
    cursor.execute("INSERT INTO Comments (task_id, user_id, comment, timestamp) VALUES (?, ?, ?, ?)",
                   (task_id, user_id, comment, datetime.now()))
    conn.commit()

def get_comments(task_id):
    cursor.execute("""
        SELECT u.username, c.comment, c.timestamp 
        FROM Comments c JOIN Users u ON c.user_id=u.user_id
        WHERE c.task_id=?
        ORDER BY c.timestamp DESC
    """, (task_id,))
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
            st.session_state.user = user
            st.success(f"Logged in as {user[1]} ({user[3]})")
            st.stop()
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")

    # --- Logout ---
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.stop()

    # Sidebar Menu
    menu = st.sidebar.radio("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # --------------------------
    # View Tasks
    # --------------------------
    if menu == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(None if user[3] in ["Admin","Manager"] else user[0])

        if tasks:
            for t in tasks:
                with st.expander(f"{t[1]} (ID: {t[0]})"):
                    st.write(f"**Title:** {t[1]}")
                    st.write(f"**Description:** {t[2]}")
                    st.write(f"**Due Date & Time:** {t[3]}")
                    st.write(f"**Status:** {t[4]}")
                    st.write(f"**Priority:** {t[5]}")
                    st.write(f"**Category:** {t[6]}")
                    st.write(f"**Assigned To (Employee ID):** {t[7]}")

                    # Mark as Completed (only if assigned user)
                    if user[0] == t[7] and t[4] != "Completed":
                        if st.button("Mark as Completed ✅", key=f"complete_{t[0]}"):
                            update_task_status(t[0], "Completed")
                            st.success("Task marked as Completed ✅")
                            st.experimental_rerun = None
                            st.stop()

                    # Comments Section
                    st.write("**Comments:**")
                    comments = get_comments(t[0])
                    for c in comments:
                        st.write(f"{c[0]} ({c[2]}): {c[1]}")

                    new_comment = st.text_input("Add Comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}") and new_comment.strip() != "":
                        add_comment(t[0], user[0], new_comment)
                        st.success("Comment added!")
                        st.stop()
        else:
            st.info("No tasks found.")

    # --------------------------
    # Overdue & Due Soon
    # --------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        st.subheader("Overdue & Due Soon Tasks")
        today = datetime.now()
        next24 = today + timedelta(hours=24)

        st.write("**Tasks Due in 24 Hours**")
        cursor.execute("""
            SELECT task_id, title, due_date, status FROM Tasks
            WHERE due_date BETWEEN ? AND ? AND status='Pending'
            ORDER BY due_date ASC
        """, (today, next24))
        due_24 = cursor.fetchall()
        if due_24:
            st.table(due_24)
        else:
            st.info("No tasks due in next 24 hours.")

        st.write("**Overdue Tasks (Not Completed)**")
        cursor.execute("""
            SELECT task_id, title, due_date, status FROM Tasks
            WHERE due_date < ? AND status='Pending'
            ORDER BY due_date ASC
        """, (today,))
        overdue = cursor.fetchall()
        if overdue:
            st.table(overdue)
        else:
            st.info("No overdue tasks.")

    # --------------------------
    # Add Task
    # --------------------------
    elif menu == "➕ Create Task":
        st.subheader("Create New Task")
        if user[3] in ["Admin","Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_datetime = datetime.combine(due_date, due_time)
            priority = st.selectbox("Priority", ["Low","Medium","High"])
            category = st.text_input("Category", "General")
            assigned_to = st.number_input("Assign to Employee ID", min_value=1, step=1)

            if st.button("Add Task"):
                add_task(assigned_to, user[0], title, description, due_datetime, priority, category)
                st.success("Task created successfully!")
                st.stop()
        else:
            st.info("Only Admin or Manager can create tasks.")
