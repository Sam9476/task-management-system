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
# Helper Functions
# --------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def get_tasks(user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks")
    else:
        cursor.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks WHERE assigned_to=?", (user[0],))
    return cursor.fetchall()

def add_task(assigned_to, title, description, due_date, priority, category):
    cursor.execute("""
        INSERT INTO Tasks (assigned_to, title, description, due_date, status, priority, category)
        VALUES (?,?,?,?,?,?,?)
    """, (assigned_to, title, description, due_date, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def add_comment(task_id, user_id, comment):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO Comments (task_id, user_id, comment, timestamp) VALUES (?,?,?,?)", (task_id, user_id, comment, timestamp))
    conn.commit()

def get_comments(task_id):
    cursor.execute("""
        SELECT u.username, c.comment, c.timestamp
        FROM Comments c
        JOIN Users u ON c.user_id=u.user_id
        WHERE c.task_id=?
        ORDER BY c.timestamp DESC
    """, (task_id,))
    return cursor.fetchall()

def get_reminder_tasks():
    today = datetime.today().date()
    next3 = today + timedelta(days=3)
    # Due soon
    cursor.execute("""
        SELECT task_id, title, due_date, status, assigned_to
        FROM Tasks
        WHERE due_date BETWEEN ? AND ? AND status='Pending'
    """, (today, next3))
    due_soon = cursor.fetchall()
    # Overdue
    cursor.execute("""
        SELECT task_id, title, due_date, status, assigned_to
        FROM Tasks
        WHERE due_date < ? AND status='Pending'
    """, (today,))
    overdue = cursor.fetchall()
    return due_soon, overdue

# --------------------------
# Streamlit App
# --------------------------
st.set_page_config(page_title="Task Management", layout="wide")
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
            st.stop()  # Refresh app
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")
    
    # Logout button
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.success("Logged out successfully")
        st.stop()  # Refresh app

    menu = st.sidebar.radio("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # --------------------------
    # All Tasks
    # --------------------------
    if menu == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(user)
        if tasks:
            for t in tasks:
                with st.expander(f"{t[1]} (ID: {t[0]}) - Status: {t[4]}"):
                    st.write(f"**Title:** {t[1]}")
                    st.write(f"**Description:** {t[2]}")
                    st.write(f"**Due Date & Time:** {t[3]}")
                    st.write(f"**Status:** {t[4]}")
                    st.write(f"**Priority:** {t[5]}")
                    st.write(f"**Category:** {t[6]}")
                    st.write(f"**Assigned To (Employee ID):** {t[7]}")
                    
                    # Mark as Completed for assigned user
                    if user[0] == t[7] and t[4] != "Completed":
                        if st.button("Mark as Completed ✅", key=f"complete_{t[0]}"):
                            update_task_status(t[0], "Completed")
                            st.success("Task marked as Completed ✅")
                            st.stop()
                    
                    # Comments
                    st.write("---")
                    st.write("**Comments / Follow-up:**")
                    comments = get_comments(t[0])
                    for c in comments:
                        st.write(f"{c[0]} ({c[2]}): {c[1]}")
                    
                    comment_text = st.text_area("Add Comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}") and comment_text.strip() != "":
                        add_comment(t[0], user[0], comment_text.strip())
                        st.success("Comment added!")
                        st.stop()
        else:
            st.info("No tasks found.")

    # --------------------------
    # Overdue & Due Soon
    # --------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        st.subheader("Overdue & Due Soon Tasks")
        due_soon, overdue = get_reminder_tasks()
        
        st.write("**Tasks Due Today / Next 3 Days**")
        if due_soon:
            df_due = pd.DataFrame(due_soon, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
            st.table(df_due)
        else:
            st.info("No tasks due soon.")

        st.write("**Overdue Tasks (Not Completed)**")
        if overdue:
            df_over = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
            st.table(df_over)
        else:
            st.info("No overdue tasks.")

    # --------------------------
    # Create Task
    # --------------------------
    elif menu == "➕ Create Task":
        st.subheader("Create Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            assigned_to = st.number_input("Assign to Employee ID", min_value=1, step=1)
            if st.button("Add Task"):
                add_task(assigned_to, title, description, due_date, priority, category)
                st.success("Task added successfully!")
                st.stop()
        else:
            st.info("Only Admin or Manager can create tasks.")
