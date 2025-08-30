import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

# -------------------------
# Database setup
# -------------------------
DB_FILE = "task_management.db"

if not os.path.exists(DB_FILE):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # Users table
    cur.execute("""
    CREATE TABLE Users (
        employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)
    # Tasks table
    cur.execute("""
    CREATE TABLE Tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id INTEGER,
        title TEXT,
        description TEXT,
        due_datetime TEXT,
        status TEXT,
        priority TEXT,
        category TEXT
    )
    """)
    # Comments table
    cur.execute("""
    CREATE TABLE Comments (
        comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        employee_id INTEGER,
        comment TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    # Insert sample users
    cur.executemany("""
    INSERT INTO Users (username, password, role) VALUES (?,?,?)
    """, [
        ("sameer", "12345", "Admin"),
        ("arnav", "abcde", "Manager"),
        ("user1", "user123", "User"),
        ("user2", "userabc", "User")
    ])
    # Insert sample tasks
    now = datetime.now()
    sample_tasks = [
        (3, "Submit Report", "Monthly sales report overdue", (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S"), "Pending", "High", "Reporting"),
        (4, "Team Meeting", "Prepare slides for team meeting", (now + timedelta(hours=20)).strftime("%Y-%m-%d %H:%M:%S"), "Pending", "Medium", "Meeting")
    ]
    cur.executemany("""
    INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category)
    VALUES (?,?,?,?,?,?,?)
    """, sample_tasks)
    conn.commit()
    conn.close()

# -------------------------
# Database connection
# -------------------------
conn = sqlite3.connect(DB_FILE, check_same_thread=False)
cursor = conn.cursor()

# -------------------------
# Helper functions
# -------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def get_tasks_for_user(user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("SELECT * FROM Tasks ORDER BY due_datetime DESC")
    else:
        cursor.execute("SELECT * FROM Tasks WHERE employee_id=? ORDER BY due_datetime DESC", (user[0],))
    return cursor.fetchall()

def get_comments(task_id):
    cursor.execute("""
        SELECT employee_id, comment, timestamp FROM Comments WHERE task_id=? ORDER BY timestamp DESC
    """, (task_id,))
    return cursor.fetchall()

def add_task(employee_id, title, description, due_datetime, priority, category):
    cursor.execute("""
        INSERT INTO Tasks (employee_id, title, description, due_datetime, status, priority, category)
        VALUES (?,?,?,?,?,?,?)
    """, (employee_id, title, description, due_datetime, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cursor.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def add_comment(task_id, employee_id, comment):
    cursor.execute("INSERT INTO Comments (task_id, employee_id, comment) VALUES (?,?,?)", (task_id, employee_id, comment))
    conn.commit()

# -------------------------
# Streamlit App
# -------------------------
st.title("📋 Task Management System")

# --- Logout button ---
if "user" in st.session_state:
    if st.sidebar.button("Logout"):
        del st.session_state.user
        st.experimental_rerun()

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

    menu = st.sidebar.selectbox("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # -------------------------
    # View all tasks
    # -------------------------
    if menu == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks_for_user(user)
        if tasks:
            for t in tasks:
                with st.expander(f"{t[2]} (ID: {t[0]})"):
                    st.write(f"**Title:** {t[2]}")
                    st.write(f"**Description:** {t[3]}")
                    st.write(f"**Due Date & Time:** {t[4]}")
                    st.write(f"**Status:** {t[5]}")
                    st.write(f"**Priority:** {t[6]}")
                    st.write(f"**Category:** {t[7]}")
                    st.write(f"**Assigned To (Employee ID):** {t[1]}")

                    # Mark as completed button (green)
                    if t[5] != "Completed" and user[0] == t[1]:
                        if st.button("Mark as Completed ✅", key=f"complete_{t[0]}"):
                            update_task_status(t[0], "Completed")
                            st.success("Task marked as Completed ✅")
                            st.experimental_rerun()

                    # Comments
                    st.subheader("Comments / Follow-up")
                    comments = get_comments(t[0])
                    for c in comments:
                        st.write(f"Employee {c[0]} ({c[2]}): {c[1]}")
                    new_comment = st.text_input("Add Comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}") and new_comment:
                        add_comment(t[0], user[0], new_comment)
                        st.success("Comment added!")
                        st.experimental_rerun()
        else:
            st.info("No tasks available.")

    # -------------------------
    # Overdue & Due Soon
    # -------------------------
    elif menu == "⚠️ Overdue & Due Soon":
        st.subheader("Overdue & Due Soon Tasks")
        now = datetime.now()
        next_24h = now + timedelta(hours=24)

        # Overdue
        cursor.execute("""
            SELECT * FROM Tasks WHERE status='Pending' AND due_datetime < ? ORDER BY due_datetime ASC
        """, (now.strftime("%Y-%m-%d %H:%M:%S"),))
        overdue = cursor.fetchall()
        st.write("**Overdue Tasks**")
        if overdue:
            for t in overdue:
                st.write(f"{t[2]} (ID: {t[0]}) - Due: {t[4]} - Assigned To: {t[1]}")
        else:
            st.write("No overdue tasks.")

        # Due in 24 hours
        cursor.execute("""
            SELECT * FROM Tasks WHERE status='Pending' AND due_datetime BETWEEN ? AND ? ORDER BY due_datetime ASC
        """, (now.strftime("%Y-%m-%d %H:%M:%S"), next_24h.strftime("%Y-%m-%d %H:%M:%S")))
        due_soon = cursor.fetchall()
        st.write("**Tasks Due in Next 24 Hours**")
        if due_soon:
            for t in due_soon:
                st.write(f"{t[2]} (ID: {t[0]}) - Due: {t[4]} - Assigned To: {t[1]}")
        else:
            st.write("No tasks due in next 24 hours.")

    # -------------------------
    # Create Task
    # -------------------------
    elif menu == "➕ Create Task":
        st.subheader("Create Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_dt = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_datetime = datetime.combine(due_dt, due_time).strftime("%Y-%m-%d %H:%M:%S")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            assign_to = st.number_input("Assign To (Employee ID)", min_value=1, step=1)
            if st.button("Add Task"):
                add_task(assign_to, title, description, due_datetime, priority, category)
                st.success("Task added successfully!")
                st.experimental_rerun()
        else:
            st.info("Only Admin or Manager can create tasks.")
