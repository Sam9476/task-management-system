# app.py
import streamlit as st
import sqlite3
from datetime import datetime, timedelta

# ------------------------
# Database connection
# ------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cur = conn.cursor()

# ------------------------
# Helper functions
# ------------------------
def login_user(username, password):
    cur.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cur.fetchone()

def get_tasks(user_id=None):
    if user_id:
        cur.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks WHERE assigned_to=?", (user_id,))
    else:
        cur.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks")
    return cur.fetchall()

def add_task(assigned_to, created_by, title, description, due_date, priority, category):
    cur.execute("""
        INSERT INTO Tasks (assigned_to, created_by, title, description, due_date, status, priority, category)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (assigned_to, created_by, title, description, due_date, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cur.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def get_comments(task_id):
    cur.execute("SELECT user_id, comment, timestamp FROM Comments WHERE task_id=? ORDER BY timestamp DESC", (task_id,))
    return cur.fetchall()

def add_comment(task_id, user_id, comment):
    cur.execute("INSERT INTO Comments (task_id, user_id, comment) VALUES (?, ?, ?)", (task_id, user_id, comment))
    conn.commit()

# ------------------------
# Streamlit App
# ------------------------
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
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.experimental_rerun()

    # Menu
    menu_options = ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"]
    choice = st.sidebar.radio("Menu", menu_options)

    # ------------------------
    # All Tasks
    # ------------------------
    if choice == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(None if user[3] in ["Admin", "Manager"] else user[0])
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
                    
                    # Mark as complete button (only for assigned user)
                    if t[7] == user[0] and t[4] != "Completed":
                        if st.button(f"Mark as Completed ✅ (Task {t[0]})", key=f"complete_{t[0]}"):
                            update_task_status(t[0], "Completed")
                            st.success("Task marked as Completed ✅")
                            st.experimental_rerun()

                    # Show comments
                    st.subheader("Comments")
                    comments = get_comments(t[0])
                    if comments:
                        for c in comments:
                            st.write(f"User {c[0]} ({c[2]}): {c[1]}")
                    # Add comment
                    comment_text = st.text_area("Add comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}") and comment_text.strip() != "":
                        add_comment(t[0], user[0], comment_text)
                        st.success("Comment added!")
                        st.experimental_rerun()

    # ------------------------
    # Overdue & Due Soon
    # ------------------------
    elif choice == "⚠️ Overdue & Due Soon":
        st.subheader("Overdue & Due Soon")
        now = datetime.now()
        soon = now + timedelta(days=1)

        # Overdue
        st.write("**Overdue Tasks:**")
        cur.execute("SELECT task_id, title, due_date, status FROM Tasks WHERE due_date < ? AND status='Pending'", (now,))
        overdue = cur.fetchall()
        st.table(overdue)

        # Due in next 24 hours
        st.write("**Tasks Due in Next 24 Hours:**")
        cur.execute("SELECT task_id, title, due_date, status FROM Tasks WHERE due_date BETWEEN ? AND ? AND status='Pending'", (now, soon))
        due_soon = cur.fetchall()
        st.table(due_soon)

    # ------------------------
    # Create Task
    # ------------------------
    elif choice == "➕ Create Task":
        st.subheader("Create Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            assigned_to = st.number_input("Assign to Employee ID", min_value=1, step=1)
            if st.button("Add Task"):
                due_datetime = datetime.combine(due_date, due_time)
                add_task(assigned_to, user[0], title, description, due_datetime, priority, category)
                st.success("Task created successfully!")
        else:
            st.info("Only Admin or Manager can create tasks.")
