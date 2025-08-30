import streamlit as st
import sqlite3
from datetime import datetime

# ------------------ DB Connection ------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cur = conn.cursor()

# ------------------ Helper Functions ------------------
def login(username, password):
    cur.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cur.fetchone()

def get_user_tasks(user):
    if user[3] in ["Admin", "Manager"]:
        cur.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks""")
    else:
        cur.execute("""SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks WHERE assigned_to=?""", (user[0],))
    return cur.fetchall()

def get_overdue_tasks(user):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if user[3] in ["Admin", "Manager"]:
        cur.execute("""SELECT task_id, title, due_date, status, assigned_to FROM Tasks WHERE due_date < ? AND status='Pending'""", (now,))
    else:
        cur.execute("""SELECT task_id, title, due_date, status FROM Tasks WHERE due_date < ? AND status='Pending' AND assigned_to=?""", (now, user[0]))
    return cur.fetchall()

def get_due_today_tasks(user):
    today_str = datetime.now().strftime("%Y-%m-%d")
    if user[3] in ["Admin", "Manager"]:
        cur.execute("""SELECT task_id, title, due_date, status, assigned_to FROM Tasks WHERE date(due_date)=? AND status='Pending'""", (today_str,))
    else:
        cur.execute("""SELECT task_id, title, due_date, status FROM Tasks WHERE date(due_date)=? AND status='Pending' AND assigned_to=?""", (today_str, user[0]))
    return cur.fetchall()

def add_task(title, description, due_date, priority, category, assigned_to, created_by):
    cur.execute("""
        INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to, created_by)
        VALUES (?, ?, ?, 'Pending', ?, ?, ?, ?)
    """, (title, description, due_date, priority, category, assigned_to, created_by))
    conn.commit()

def mark_task_complete(task_id):
    cur.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
    conn.commit()

# ------------------ Streamlit UI ------------------
st.title("📋 Task Management System")

# ---------- Login ----------
if "user" not in st.session_state:
    st.subheader("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login(username, password)
        if user:
            st.session_state.user = user
            st.success(f"Logged in as {user[1]} ({user[3]})")
        else:
            st.error("Invalid credentials")
else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")
    if st.sidebar.button("Logout"):
        st.session_state.pop("user")
        st.experimental_rerun()

    menu = st.sidebar.radio("Menu", ["View Tasks", "Overdue & Due Today Tasks", "Create Task"])

    # ------------------ View Tasks ------------------
    if menu == "View Tasks":
        st.subheader("All Tasks")
        tasks = get_user_tasks(user)
        import pandas as pd
        if tasks:
            df = pd.DataFrame(tasks, columns=["Task ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"])
            st.table(df)
        else:
            st.info("No tasks available.")

    # ------------------ Overdue & Due Today ------------------
    elif menu == "Overdue & Due Today Tasks":
        st.subheader("Overdue Tasks")
        overdue = get_overdue_tasks(user)
        if overdue:
            import pandas as pd
            df_overdue = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"] if user[3] in ["Admin","Manager"] else ["Task ID", "Title", "Due Date", "Status"])
            st.table(df_overdue)
        else:
            st.info("No overdue tasks.")

        st.subheader("Tasks Due Today")
        due_today = get_due_today_tasks(user)
        if due_today:
            import pandas as pd
            df_today = pd.DataFrame(due_today, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"] if user[3] in ["Admin","Manager"] else ["Task ID", "Title", "Due Date", "Status"])
            st.table(df_today)
        else:
            st.info("No tasks due today.")

    # ------------------ Create Task ------------------
    elif menu == "Create Task":
        if user[3] in ["Admin","Manager"]:
            st.subheader("Create Task")
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Due Time")
            due_datetime = f"{due_date} {due_time}"
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            # Only assign to users below or equal authority
            cur.execute("SELECT user_id, username, role FROM Users")
            all_users = cur.fetchall()
            assign_options = {u[1]: u[0] for u in all_users if u[2] != "Admin" or user[3]=="Admin"}
            assigned_to = st.selectbox("Assign To", list(assign_options.keys()))
            if st.button("Create Task"):
                add_task(title, description, due_datetime, priority, category, assign_options[assigned_to], user[0])
                st.success("Task created successfully!")
        else:
            st.info("Only Admin or Manager can create tasks.")
