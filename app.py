import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
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

def highlight_status(val):
    if val == "Pending":
        return "background-color: #fde68a; color: black;"
    elif val == "Completed":
        return "background-color: #86efac; color: black;"
    elif val == "Overdue":
        return "background-color: #fca5a5; color: black;"
    return ""

def format_datetime(dt):
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except:
            return dt
    return dt.strftime("%d-%b-%Y %H:%M") if dt else ""

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
    st.sidebar.header("📌 Navigation")
    st.sidebar.write(f"👤 {user[1]} ({user[3]})")

    # --- Fetch Tasks ---
    tasks = get_tasks(user)
    df_tasks = pd.DataFrame(tasks, columns=["Task ID", "Title", "Description", "Due Date",
                                            "Status", "Priority", "Category", "Assigned To"])
    today = datetime.today().date()
    if not df_tasks.empty:
        df_tasks['Due Date'] = pd.to_datetime(df_tasks['Due Date'], errors='coerce')
        df_tasks.loc[(df_tasks['Due Date'].dt.date < today) & (df_tasks['Status'] == 'Pending'), 'Status'] = 'Overdue'

    # --- Sidebar Counts ---
    total_tasks = len(df_tasks)
    pending_count = df_tasks[df_tasks['Status'] == 'Pending'].shape[0]
    completed_count = df_tasks[df_tasks['Status'] == 'Completed'].shape[0]
    overdue_count = df_tasks[df_tasks['Status'] == 'Overdue'].shape[0]
    today_count = df_tasks[df_tasks['Due Date'].dt.date == today].shape[0] if not df_tasks.empty else 0

    st.sidebar.markdown("### 📝 Task Overview")
    st.sidebar.markdown(f"Total: **{total_tasks}**")
    st.sidebar.markdown(f"🟡 Pending: **{pending_count}**")
    st.sidebar.markdown(f"🟢 Completed: **{completed_count}**")
    st.sidebar.markdown(f"🔴 Overdue: **{overdue_count}**")
    st.sidebar.markdown(f"🟡 Due Today: **{today_count}**")

    menu = st.sidebar.radio("Go to", ["View Tasks", "Overdue & Today Tasks", "Create Task", "Logout"])

    # --- Logout ---
    if menu == "Logout":
        st.session_state.clear()
        st.success("✅ You have been logged out.")
        time.sleep(1)
        st.rerun()

    # --- View Tasks ---
    elif menu == "View Tasks":
        st.subheader("📋 All Tasks")
        if not df_tasks.empty:
            df_tasks['Due Date'] = df_tasks['Due Date'].apply(lambda x: format_datetime(x) if pd.notnull(x) else "")
            st.dataframe(df_tasks.style.applymap(highlight_status, subset=["Status"]),
                         use_container_width=True, height=min(400, 50 + len(df_tasks)*35))
        else:
            st.info("ℹ️ No tasks found.")

        if user[3] not in ["Admin", "Manager"] and not df_tasks.empty:
            st.subheader("✅ Mark Task as Completed")
            task_id_to_complete = st.number_input("Enter Task ID", min_value=1, step=1)
            if st.button("Mark as Complete"):
                if mark_task_complete(task_id_to_complete, user):
                    st.success(f"Task {task_id_to_complete} completed 🎉")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Not authorized or task not found.")

        if user[3] in ["Admin", "Manager"] and not df_tasks.empty:
            st.subheader("🗑️ Delete Task")
            task_id_to_delete = st.number_input("Enter Task ID to delete", min_value=1, step=1, key="delete")
            with st.expander("⚠️ Confirm Deletion"):
                with st.form("delete_form", clear_on_submit=True):
                    st.warning(f"Are you sure you want to delete Task ID {task_id_to_delete}? This cannot be undone.")
                    confirm = st.radio("Please confirm:", ["No", "Yes"], index=0, key="confirm_delete")
                    submitted = st.form_submit_button("Delete Task")
                    if submitted:
                        if confirm == "Yes":
                            if delete_task(task_id_to_delete, user):
                                st.success(f"🗑️ Task {task_id_to_delete} deleted successfully!")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error("❌ Task not found.")
                        else:
                            st.info("Delete cancelled.")

    # --- Overdue & Today Tasks ---
    elif menu == "Overdue & Today Tasks":
        st.subheader("⚠️ Deadlines Overview")
        if not df_tasks.empty:
            # Overdue tasks
            df_overdue = df_tasks[df_tasks['Status'] == 'Overdue']
            st.markdown("### 🔴 Overdue Tasks")
            if not df_overdue.empty:
                st.dataframe(df_overdue.style.applymap(highlight_status, subset=["Status"]),
                             use_container_width=True, height=min(250, 50 + len(df_overdue)*35))
            else:
                st.success("🎉 No overdue tasks!")

            df_today = df_tasks[df_tasks['Due Date'].dt.date == today]
            st.markdown("### 🟡 Tasks Due Today")
            if not df_today.empty:
                st.dataframe(df_today.style.applymap(highlight_status, subset=["Status"]),
                             use_container_width=True, height=min(250, 50 + len(df_today)*35))
            else:
                st.info("No tasks due today.")
        else:
            st.info("No tasks found.")

    # --- Create Task ---
    elif menu == "Create Task":
        st.subheader("➕ Create New Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title *")
            description = st.text_area("Description *")
            due_date = st.date_input("Due Date *")
            due_time = st.time_input("Time *")
            priority = st.selectbox("Priority *", ["Low","Medium","High"])
            category = st.text_input("Category","General")
            due_datetime = datetime.combine(due_date,due_time)

            cursor.execute("SELECT user_id, username FROM Users WHERE role NOT IN ('Admin','Manager')")
            users_list = cursor.fetchall()

            if users_list:
                assign_to_name = st.selectbox("Assign To *",[u[1] for u in users_list])
                assign_to = [u[0] for u in users_list if u[1]==assign_to_name][0]

                if st.button("Add Task"):
                    if not title.strip() or not description.strip():
                        st.error("❌ All required fields must be filled.")
                    else:
                        if add_task(user,title,description,due_datetime,priority,category,assign_to):
                            st.success("✅ Task created successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Not authorized.")
            else:
                st.warning("No users available to assign.")
        else:
            st.info("Only Admin/Manager can create tasks.")


