import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time

# --------------------------
# Database Connection
# --------------------------
conn = sqlite3.connect("task_management.db", check_same_thread=False)
cursor = conn.cursor()

# --------------------------
# Custom Styling (CSS)
# --------------------------
st.markdown("""
    <style>
    .stApp {background: linear-gradient(135deg, #f0f4f8, #d9e2ec);}
    h1, h2, h3, h4 {color: #1e3a8a; font-family: 'Segoe UI', sans-serif;}
    section[data-testid="stSidebar"] {background-color: #1e293b;}
    section[data-testid="stSidebar"] * {color: white !important;}
    .dataframe {border-collapse: collapse; border-radius: 12px; overflow: hidden;
                box-shadow: 0px 2px 8px rgba(0,0,0,0.1);}
    .dataframe th {background: #1e3a8a; color: white !important; text-align: center; padding: 8px;}
    .dataframe td {padding: 8px; text-align: center; background: #f9fafb;}
    .stSuccess {background-color: #dcfce7 !important; color: #166534 !important; border-radius: 10px;}
    .stError {background-color: #fee2e2 !important; color: #991b1b !important; border-radius: 10px;}
    button {border-radius: 8px !important; padding: 0.6em 1.2em; font-weight: bold;}
    </style>
""", unsafe_allow_html=True)

# --------------------------
# Helper Functions
# --------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def get_tasks(user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status,
                   t.priority, t.category, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to = u.user_id
        """)
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status,
                   t.priority, t.category, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to = u.user_id
            WHERE t.assigned_to = ?
        """, (user[0],))
    return cursor.fetchall()

def add_task(creator, title, description, due_date, priority, category, assign_to):
    if creator[3] in ["Admin", "Manager"]:
        cursor.execute("""
            INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to, created_by)
            VALUES (?,?,?,?,?,?,?,?)
        """, (title, description, due_date, "Pending", priority, category, assign_to, creator[0]))
        conn.commit()
        return True
    return False

def update_task(task_id, user, title=None, description=None, due_date=None, priority=None, category=None):
    cursor.execute("SELECT * FROM Tasks WHERE task_id=?", (task_id,))
    task = cursor.fetchone()
    if not task:
        return False
    if user[3] in ["Admin", "Manager"]:
        updates = []
        params = []
        if title: updates.append("title=?"); params.append(title)
        if description: updates.append("description=?"); params.append(description)
        if due_date: updates.append("due_date=?"); params.append(due_date)
        if priority: updates.append("priority=?"); params.append(priority)
        if category: updates.append("category=?"); params.append(category)
        params.append(task_id)
        if updates:
            cursor.execute(f"UPDATE Tasks SET {', '.join(updates)} WHERE task_id=?", params)
            conn.commit()
            return True
    return False

def mark_task_complete(task_id, user):
    cursor.execute("SELECT assigned_to FROM Tasks WHERE task_id=?", (task_id,))
    result = cursor.fetchone()
    if result and user[0] == result[0]:
        cursor.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
        conn.commit()
        return True
    return False

def delete_task(task_id, user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("SELECT * FROM Tasks WHERE task_id=?", (task_id,))
        if cursor.fetchone():
            cursor.execute("DELETE FROM Tasks WHERE task_id=?", (task_id,))
            conn.commit()
            return True
    return False

def get_overdue_and_today_tasks(user):
    today = datetime.today().date()
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date < ? AND t.status='Pending'
        """, (today,))
        overdue = cursor.fetchall()
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date = ? AND t.status='Pending'
        """, (today,))
        today_tasks = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date < ? AND t.status='Pending' AND t.assigned_to=?
        """, (today, user[0]))
        overdue = cursor.fetchall()
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.due_date = ? AND t.status='Pending' AND t.assigned_to=?
        """, (today, user[0]))
        today_tasks = cursor.fetchall()
    return overdue, today_tasks

def highlight_status(val):
    if val == "Pending": return "background-color: #fde68a; color: black;"
    elif val == "Completed": return "background-color: #86efac; color: black;"
    elif val == "Overdue": return "background-color: #fca5a5; color: black;"
    return ""

def format_datetime(dt):
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%d-%b-%Y %H:%M")

# --------------------------
# Streamlit App
# --------------------------
st.title("📋 Task Management System")

# --- Login ---
if "user" not in st.session_state:
    st.subheader("🔑 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state.user = user
            st.success(f"✅ Logged in as {user[1]} ({user[3]})")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
else:
    user = st.session_state.user

    # Sidebar
    st.sidebar.header("📌 Navigation")
    st.sidebar.write(f"👤 {user[1]} ({user[3]})")

    tasks = get_tasks(user)
    df_tasks = pd.DataFrame(tasks, columns=["Task ID", "Title", "Description", "Due Date",
                                            "Status", "Priority", "Category", "Assigned To"])
    total_tasks = len(df_tasks)
    pending_count = df_tasks[df_tasks['Status']=='Pending'].shape[0]
    completed_count = df_tasks[df_tasks['Status']=='Completed'].shape[0]
    overdue_count = df_tasks[df_tasks['Status']=='Overdue'].shape[0]
    today = datetime.today().date()
    today_count = df_tasks[pd.to_datetime(df_tasks['Due Date']).dt.date==today].shape[0]

    st.sidebar.markdown("### 📝 Task Overview")
    st.sidebar.markdown(f"Total: **{total_tasks}**")
    st.sidebar.markdown(f"🟡 Pending: **{pending_count}**")
    st.sidebar.markdown(f"🟢 Completed: **{completed_count}**")
    st.sidebar.markdown(f"🔴 Overdue: **{overdue_count}**")
    st.sidebar.markdown(f"🟡 Due Today: **{today_count}**")

    menu = st.sidebar.radio("Go to", [
        "View Tasks", "Overdue & Today Tasks", "Create Task",
        "Update Task", "Ask Follow-up Question", "Logout"
    ])

    # --- Logout ---
    if menu == "Logout":
        st.session_state.clear()
        st.success("✅ Logged out")
        time.sleep(1)
        st.rerun()

    # --- View Tasks ---
    elif menu == "View Tasks":
        st.subheader("📋 All Tasks")
        if tasks:
            df_tasks['Due Date'] = df_tasks['Due Date'].apply(format_datetime)
            df_tasks.loc[pd.to_datetime(df_tasks['Due Date']).dt.date < today, 'Status'] = 'Overdue'
            st.dataframe(df_tasks.style.applymap(highlight_status, subset=["Status"]),
                         use_container_width=True, height=400)
        else:
            st.info("ℹ️ No tasks found.")

    # --- Overdue & Today Tasks ---
    elif menu == "Overdue & Today Tasks":
        st.subheader("⚠️ Deadlines Overview")
        overdue, today_tasks = get_overdue_and_today_tasks(user)
        st.markdown("### 🔴 Overdue Tasks")
        if overdue:
            df_overdue = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
            df_overdue['Status'] = 'Overdue'
            df_overdue['Due Date'] = df_overdue['Due Date'].apply(format_datetime)
            st.dataframe(df_overdue.style.applymap(highlight_status, subset=["Status"]), use_container_width=True, height=250)
        else:
            st.success("🎉 No overdue tasks!")
        st.markdown("### 🟡 Tasks Due Today")
        if today_tasks:
            df_today = pd.DataFrame(today_tasks, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
            df_today['Due Date'] = df_today['Due Date'].apply(format_datetime)
            st.dataframe(df_today.style.applymap(highlight_status, subset=["Status"]), use_container_width=True, height=250)
        else:
            st.info("No tasks due today.")

    # --- Create Task ---
    elif menu == "Create Task":
        st.subheader("➕ Create New Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            due_time = st.time_input("Time")
            priority = st.selectbox("Priority", ["Low", "Medium", "High"])
            category = st.text_input("Category", "General")
            due_datetime = datetime.combine(due_date, due_time)

            cursor.execute("SELECT user_id, username FROM Users WHERE user_id != ?", (user[0],))
            users_list = cursor.fetchall()
            if users_list:
                assign_to_name = st.selectbox("Assign To", [u[1] for u in users_list])
                assign_to = [u[0] for u in users_list if u[1]==assign_to_name][0]

                if st.button("Add Task"):
                    if add_task(user, title, description, due_datetime, priority, category, assign_to):
                        st.success("✅ Task created successfully!")
                        time.sleep(1)
                        st.rerun()
            else:
                st.warning("No users available to assign.")
        else:
            st.info("Only Admin/Manager can create tasks.")

    # --- Update Task ---
    elif menu == "Update Task":
        st.subheader("✏️ Update Existing Task")
        if user[3] in ["Admin", "Manager"]:
            task_id_to_update = st.number_input("Enter Task ID to update", min_value=1, step=1)
            task_data = None
            if task_id_to_update:
                cursor.execute("SELECT title, description, due_date, priority, category FROM Tasks WHERE task_id=?", (task_id_to_update,))
                task_data = cursor.fetchone()
            if task_data:
                title = st.text_input("Title", value=task_data[0])
                description = st.text_area("Description", value=task_data[1])
                due_dt = datetime.fromisoformat(task_data[2])
                due_date = st.date_input("Due Date", value=due_dt.date())
                due_time = st.time_input("Time", value=due_dt.time())
                priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=["Low","Medium","High"].index(task_data[3]))
                category = st.text_input("Category", value=task_data[4])
                new_datetime = datetime.combine(due_date, due_time)
                if st.button("Update Task"):
                    if update_task(task_id_to_update, user, title, description, new_datetime, priority, category):
                        st.success("✅ Task updated successfully")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Task update failed")
            else:
                st.warning("❌ Invalid Task ID")

    # --- Ask Follow-up Question ---
    elif menu == "Ask Follow-up Question":
        st.subheader("💬 Ask a Follow-up Question")
        task_id_for_comment = st.number_input("Enter Task ID", min_value=1, step=1)
        comment = st.text_area("Type your comment here")
        valid_task = False
        if task_id_for_comment:
            cursor.execute("SELECT * FROM Tasks WHERE task_id=?",(task_id_for_comment,))
            task_exists = cursor.fetchone()
            if task_exists:
                valid_task = True
        if st.button("Submit Comment"):
            if valid_task and comment.strip():
                # Here: you can insert into FollowUpComments table if exists
                st.success("✅ Comment submitted!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Invalid Task ID or empty comment")
