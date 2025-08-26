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
    user = cursor.fetchone()
    return user  # None if not found

def get_tasks(user_id=None):
    if user_id:
        cursor.execute("SELECT task_id, title, description, due_date, status, priority, category FROM Tasks WHERE user_id=?", (user_id,))
    else:
        cursor.execute("SELECT task_id, title, description, due_date, status, priority, category FROM Tasks")
    return cursor.fetchall()

def add_task(user_id, title, description, due_date, priority, category):
    cursor.execute("""
        INSERT INTO Tasks (user_id, title, description, due_date, status, priority, category)
        VALUES (?,?,?,?,?,?)
    """, (user_id, title, description, due_date, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def add_comment(task_id, user_id, comment):
    cursor.execute("INSERT INTO Comments (task_id, user_id, comment) VALUES (?,?,?)", (task_id, user_id, comment))
    conn.commit()

def get_comments(task_id):
    cursor.execute("""
        SELECT c.comment, u.username, c.timestamp 
        FROM Comments c JOIN Users u ON c.user_id=u.user_id
        WHERE c.task_id=?
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
            st.success(f"Logged in as {user[1]} ({user[4]})")
            st.session_state.user = user
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[4]})")

    menu = st.sidebar.selectbox("Menu", ["View Tasks", "Add Task", "Update Task Status", "Add Comment", "Reminders"])
    
    # --------------------------
    # View Tasks
    # --------------------------
    if menu == "View Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks() if user[4] in ["Admin","Manager"] else get_tasks(user[0])
        
        if tasks:
            df = pd.DataFrame(tasks, columns=["Task ID", "Title", "Description", "Due Date", "Status", "Priority", "Category"])
            st.table(df)
        else:
            st.info("No tasks found.")


    # --------------------------
    # Add Task
    # --------------------------
    elif menu == "Add Task":
        st.subheader("Add Task")
        if user[4] in ["Admin","Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            assign_to = st.number_input("Assign to User ID", min_value=1, step=1)
            if st.button("Add Task"):
                add_task(assign_to, title, description, due_date, priority, category)
                st.success("Task added successfully!")
        else:
            st.info("Only Admin or Manager can add tasks.")

    # --------------------------
    # Update Task Status
    # --------------------------
    elif menu == "Update Task Status":
        st.subheader("Update Task Status")
        task_id = st.number_input("Task ID", min_value=1, step=1)
        status = st.selectbox("Status", ["Pending","Completed"])
        if st.button("Update Status"):
            update_task_status(task_id, status)
            st.success("Task status updated!")

    # --------------------------
    # Add Comment
    # --------------------------
    elif menu == "Add Comment":
        st.subheader("Add Comment")
        task_id = st.number_input("Task ID", min_value=1, step=1)
        comment = st.text_area("Comment")
        if st.button("Post Comment"):
            add_comment(task_id, user[0], comment)
            st.success("Comment added!")

        # Show existing comments
        st.subheader("Existing Comments")
        comments = get_comments(task_id)
        for c in comments:
            st.write(f"{c[1]} ({c[2]}): {c[0]}")

    # --------------------------
    # Reminders
    # --------------------------
    elif menu == "Reminders":
        st.subheader("Reminders")

        today = datetime.today().date()
        next3 = today + timedelta(days=3)

        st.write("**Tasks Due Today / Next 3 Days**")
        cursor.execute("""
            SELECT task_id, title, due_date, status FROM Tasks 
            WHERE due_date BETWEEN ? AND ? AND status='Pending'
        """, (today, next3))
        due_tasks = cursor.fetchall()
        st.table(due_tasks)

        st.write("**Overdue Tasks (Not Completed)**")
        cursor.execute("""
            SELECT task_id, title, due_date, status FROM Tasks 
            WHERE due_date < ? AND status='Pending'
        """, (today,))
        overdue_tasks = cursor.fetchall()
        st.table(overdue_tasks)


