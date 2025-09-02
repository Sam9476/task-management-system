# app.py - Final version (Streamlit)
# Features:
# - Login/logout with roles (Admin/Manager/User)
# - View tasks (role-based), color-coded status badges, formatted dates
# - Create task (Admin/Manager) with date+time, cannot assign to self
# - Update task (Admin/Manager) — enter Task ID to auto-load fields, validate ID
# - Mark task complete (assigned user only)
# - Delete task (Admin/Manager)
# - Overdue / Tasks due today (separate lists)
# - Ask follow-up comment (must supply valid Task ID and non-empty comment)
# - Comments saved and shown per task
# - Tables are scrollable, no empty rows, messages shown then page reruns
# - Uses SQLite (task_management.db). Creates tables if missing (safe)

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import os

DB_PATH = "task_management.db"

# --------------------------
# Ensure DB + Tables Exist (safe - won't overwrite existing data)
# --------------------------
def init_db(path=DB_PATH):
    new_db = not os.path.exists(path)
    conn_local = sqlite3.connect(path, check_same_thread=False)
    cur = conn_local.cursor()
    # Users table (minimal columns used by app)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )
    """)
    # Tasks table (stores due_date as ISO datetime string)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Tasks (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            due_date TEXT,
            status TEXT,
            priority TEXT,
            category TEXT,
            assigned_to INTEGER,
            created_by INTEGER,
            FOREIGN KEY (assigned_to) REFERENCES Users(user_id),
            FOREIGN KEY (created_by) REFERENCES Users(user_id)
        )
    """)
    # Comments table (follow-up questions)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            user_id INTEGER,
            comment TEXT,
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES Tasks(task_id),
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        )
    """)
    conn_local.commit()
    return conn_local, cur

conn, cursor = init_db(DB_PATH)

# --------------------------
# Small helper utilities
# --------------------------
def format_datetime(dt_iso):
    if pd.isna(dt_iso):
        return ""
    if isinstance(dt_iso, (int, float)):
        return ""
    try:
        # If stored as ISO str
        dt = datetime.fromisoformat(dt_iso)
    except Exception:
        try:
            # fallback parse by pandas
            dt = pd.to_datetime(dt_iso)
        except Exception:
            return str(dt_iso)
    return dt.strftime("%d-%b-%Y %H:%M")

def parse_datetime_to_iso(date_obj, time_obj):
    combined = datetime.combine(date_obj, time_obj)
    return combined.isoformat()

# --------------------------
# DB helper functions
# --------------------------
def login_user(username, password):
    cursor.execute("SELECT * FROM Users WHERE username=? AND password=?", (username, password))
    return cursor.fetchone()

def get_tasks(user):
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status,
                   t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.user_id
            ORDER BY t.task_id
        """)
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.description, t.due_date, t.status,
                   t.priority, t.category, u.username
            FROM Tasks t
            JOIN Users u ON t.assigned_to = u.user_id
            WHERE t.assigned_to = ?
            ORDER BY t.task_id
        """, (user[0],))
    rows = cursor.fetchall()
    return rows

def get_task_by_id(task_id):
    cursor.execute("SELECT * FROM Tasks WHERE task_id=?", (task_id,))
    return cursor.fetchone()

def add_task(creator, title, description, due_iso, priority, category, assign_to):
    if creator[3] not in ["Admin", "Manager"]:
        return False
    cursor.execute("""
        INSERT INTO Tasks (title, description, due_date, status, priority, category, assigned_to, created_by)
        VALUES (?,?,?,?,?,?,?,?)
    """, (title, description, due_iso, "Pending", priority, category, assign_to, creator[0]))
    conn.commit()
    return True

def update_task(task_id, user, title=None, description=None, due_iso=None, priority=None, category=None):
    task = get_task_by_id(task_id)
    if not task or user[3] not in ["Admin", "Manager"]:
        return False
    updates = []
    params = []
    if title is not None:
        updates.append("title=?"); params.append(title)
    if description is not None:
        updates.append("description=?"); params.append(description)
    if due_iso is not None:
        updates.append("due_date=?"); params.append(due_iso)
    if priority is not None:
        updates.append("priority=?"); params.append(priority)
    if category is not None:
        updates.append("category=?"); params.append(category)
    if not updates:
        return False
    params.append(task_id)
    cursor.execute(f"UPDATE Tasks SET {', '.join(updates)} WHERE task_id=?", params)
    conn.commit()
    return True

def mark_task_complete(task_id, user):
    cursor.execute("SELECT assigned_to FROM Tasks WHERE task_id=?", (task_id,))
    res = cursor.fetchone()
    if not res:
        return False
    assigned_to = res[0]
    if assigned_to != user[0]:
        return False
    cursor.execute("UPDATE Tasks SET status='Completed' WHERE task_id=?", (task_id,))
    conn.commit()
    return True

def delete_task(task_id, user):
    if user[3] not in ["Admin", "Manager"]:
        return False
    cursor.execute("SELECT * FROM Tasks WHERE task_id=?", (task_id,))
    if not cursor.fetchone():
        return False
    cursor.execute("DELETE FROM Tasks WHERE task_id=?", (task_id,))
    conn.commit()
    return True

def get_overdue_and_today_tasks(user):
    today = datetime.today().date()
    if user[3] in ["Admin", "Manager"]:
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.status='Pending'
            ORDER BY t.due_date
        """)
        all_tasks = cursor.fetchall()
    else:
        cursor.execute("""
            SELECT t.task_id, t.title, t.due_date, t.status, u.username
            FROM Tasks t JOIN Users u ON t.assigned_to=u.user_id
            WHERE t.status='Pending' AND t.assigned_to=?
            ORDER BY t.due_date
        """, (user[0],))
        all_tasks = cursor.fetchall()

    overdue = []
    today_list = []
    for t in all_tasks:
        try:
            due_dt = datetime.fromisoformat(t[2])
        except Exception:
            try:
                due_dt = pd.to_datetime(t[2])
            except Exception:
                continue
        if due_dt.date() < today:
            overdue.append(t)
        elif due_dt.date() == today:
            today_list.append(t)
    return overdue, today_list

# Comments
def add_comment(task_id, user_id, text):
    if not text or text.strip() == "":
        return False
    cursor.execute("SELECT task_id FROM Tasks WHERE task_id=?", (task_id,))
    if not cursor.fetchone():
        return False
    timestamp = datetime.now().isoformat(sep=' ')
    cursor.execute("INSERT INTO Comments (task_id, user_id, comment, timestamp) VALUES (?,?,?,?)",
                   (task_id, user_id, text.strip(), timestamp))
    conn.commit()
    return True

def get_comments(task_id):
    cursor.execute("""
        SELECT c.comment, u.username, c.timestamp
        FROM Comments c JOIN Users u ON c.user_id=u.user_id
        WHERE c.task_id=?
        ORDER BY c.comment_id DESC
    """, (task_id,))
    return cursor.fetchall()

# --------------------------
# UI Styling (minimal, light mode)
# --------------------------
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg,#f7fafc,#eef2f7); }
    section[data-testid="stSidebar"] { background-color: #0f172a; color: white; }
    section[data-testid="stSidebar"] .css-1d391kg { color: white; }
    .dataframe th { background: #0f172a !important; color: white !important; }
    </style>
""", unsafe_allow_html=True)

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
            time.sleep(2)
            st.rerun()
        else:
            st.error("❌ Invalid credentials")
    st.stop()

# After login
user = st.session_state.user

# Sidebar - navigation and task overview
st.sidebar.header("📌 Navigation")
st.sidebar.write(f"👤 {user[1]} ({user[3]})")

# Fetch tasks fresh
tasks = get_tasks(user)
# Build dataframe safely
df_tasks = pd.DataFrame(tasks, columns=[
    "Task ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"
]) if tasks else pd.DataFrame(columns=[
    "Task ID", "Title", "Description", "Due Date", "Status", "Priority", "Category", "Assigned To"
])

# Normalize statuses (mark overdue dynamically)
today_date = datetime.today().date()
def compute_status(row):
    status = row["Status"]
    try:
        due_iso = row["Due Date"]
        if pd.isna(due_iso) or due_iso == "":
            return status
        due_dt = datetime.fromisoformat(due_iso)
        if status != "Completed" and due_dt.date() < today_date:
            return "Overdue"
    except Exception:
        pass
    return status

if not df_tasks.empty:
    df_tasks["Status"] = df_tasks.apply(compute_status, axis=1)

# Sidebar overview counts
total_tasks = len(df_tasks)
pending_count = (df_tasks["Status"] == "Pending").sum() if "Status" in df_tasks else 0
completed_count = (df_tasks["Status"] == "Completed").sum() if "Status" in df_tasks else 0
overdue_count = (df_tasks["Status"] == "Overdue").sum() if "Status" in df_tasks else 0
due_today_count = 0
if not df_tasks.empty:
    try:
        due_today_count = pd.to_datetime(df_tasks["Due Date"]).dt.date.eq(today_date).sum()
    except Exception:
        due_today_count = 0

st.sidebar.markdown("### 📝 Task Overview")
st.sidebar.markdown(f"Total: **{total_tasks}**")
st.sidebar.markdown(f"🟡 Pending: **{int(pending_count)}**")
st.sidebar.markdown(f"🟢 Completed: **{int(completed_count)}**")
st.sidebar.markdown(f"🔴 Overdue: **{int(overdue_count)}**")
st.sidebar.markdown(f"🟡 Due Today: **{int(due_today_count)}**")

# Navigation - ordered
menu = st.sidebar.radio("Go to", [
    "View Tasks",
    "Overdue Tasks",
    "Tasks Due Today",
    "Create Task",
    "Update Task",
    "Ask Follow-up Question",
    "Logout"
])

# Helper for styled dataframe display (status badges)
def style_status(df):
    def status_style(v):
        if v == "Pending":
            return "background-color: #fde68a; color: black;"
        if v == "Completed":
            return "background-color: #86efac; color: black;"
        if v == "Overdue":
            return "background-color: #fca5a5; color: black;"
        return ""
    return df.style.applymap(status_style, subset=["Status"])

# --------------------------
# VIEW TASKS
# --------------------------
if menu == "View Tasks":
    st.subheader("📋 All Tasks")
    if not df_tasks.empty:
        df_display = df_tasks.copy()
        # format due dates
        df_display["Due Date"] = df_display["Due Date"].apply(lambda x: format_datetime(x) if x else "")
        st.dataframe(style_status(df_display), use_container_width=True, height=420)
    else:
        st.info("No tasks found.")

    # mark complete (only for assigned user)
    if user[3] not in ["Admin", "Manager"] and not df_tasks.empty:
        st.subheader("✅ Mark Task as Completed")
        task_id_to_complete = st.number_input("Task ID to mark complete", min_value=1, step=1, key="mc")
        if st.button("Mark as Complete"):
            ok = mark_task_complete(task_id_to_complete, user)
            if ok:
                st.success(f"Task {task_id_to_complete} marked as Completed ✅")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Not authorized, task not found, or you are not the assigned user.")

    # delete (Admin/Manager)
    if user[3] in ["Admin", "Manager"] and not df_tasks.empty:
        st.subheader("🗑️ Delete Task")
        task_id_to_delete = st.number_input("Task ID to delete", min_value=1, step=1, key="del")
        if st.button("Delete Task"):
            ok = delete_task(task_id_to_delete, user)
            if ok:
                st.success(f"Task {task_id_to_delete} deleted ✅")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Task not found or you are not authorized.")

# --------------------------
# OVERDUE TASKS
# --------------------------
elif menu == "Overdue Tasks":
    st.subheader("🔴 Overdue Tasks")
    overdue, _ = get_overdue_and_today_tasks(user)
    if overdue:
        df_over = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
        df_over["Status"] = "Overdue"
        df_over["Due Date"] = df_over["Due Date"].apply(lambda x: format_datetime(x))
        st.dataframe(style_status(df_over), use_container_width=True, height=350)
    else:
        st.success("No overdue tasks! 🎉")

# --------------------------
# TASKS DUE TODAY
# --------------------------
elif menu == "Tasks Due Today":
    st.subheader("🟡 Tasks Due Today")
    _, today_tasks = get_overdue_and_today_tasks(user)
    if today_tasks:
        df_today = pd.DataFrame(today_tasks, columns=["Task ID", "Title", "Due Date", "Status", "Assigned To"])
        df_today["Due Date"] = df_today["Due Date"].apply(lambda x: format_datetime(x))
        st.dataframe(style_status(df_today), use_container_width=True, height=350)
    else:
        st.info("No tasks due today.")

# --------------------------
# CREATE TASK
# --------------------------
elif menu == "Create Task":
    st.subheader("➕ Create Task")
    if user[3] in ["Admin", "Manager"]:
        title = st.text_input("Title")
        description = st.text_area("Description")
        due_date = st.date_input("Due Date")
        due_time = st.time_input("Time")
        priority = st.selectbox("Priority", ["Low", "Medium", "High"], index=1)
        category = st.text_input("Category", "General")
        # assign to users excluding self
        cursor.execute("SELECT user_id, username FROM Users WHERE user_id != ?", (user[0],))
        users_list = cursor.fetchall()
        if not users_list:
            st.warning("No other users available to assign.")
        else:
            assign_to_name = st.selectbox("Assign To", [u[1] for u in users_list])
            assign_to = [u[0] for u in users_list if u[1] == assign_to_name][0]
            if st.button("Add Task"):
                if not title.strip():
                    st.error("Title cannot be empty.")
                else:
                    due_iso = parse_datetime_to_iso(due_date, due_time)
                    ok = add_task(user, title.strip(), description.strip(), due_iso, priority, category.strip(), assign_to)
                    if ok:
                        st.success("Task created ✅")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("You are not authorized to create tasks.")
    else:
        st.info("Only Admin/Manager can create tasks.")

# --------------------------
# UPDATE TASK
# --------------------------
elif menu == "Update Task":
    st.subheader("✏️ Update Task (Admin/Manager)")
    if user[3] in ["Admin", "Manager"]:
        task_id_to_update = st.number_input("Enter Task ID", min_value=1, step=1, key="up_id")
        if st.button("Fetch Task"):
            task = get_task_by_id(task_id_to_update)
            if not task:
                st.error("Invalid Task ID.")
            else:
                # store fetched in session to show form
                st.session_state["fetched_task"] = task
                st.experimental_rerun()

        fetched = st.session_state.get("fetched_task", None)
        if fetched and fetched[0] == task_id_to_update:
            # task columns: (task_id, title, description, due_date, status, priority, category, assigned_to, created_by)
            _, cur_title, cur_desc, cur_due_iso, cur_status, cur_priority, cur_category, cur_assigned_to, _ = fetched
            due_dt = None
            try:
                due_dt = datetime.fromisoformat(cur_due_iso)
            except Exception:
                due_dt = datetime.now()
            title_new = st.text_input("Title", value=cur_title)
            desc_new = st.text_area("Description", value=cur_desc)
            due_date_new = st.date_input("Due Date", value=due_dt.date())
            due_time_new = st.time_input("Time", value=due_dt.time())
            priority_new = st.selectbox("Priority", ["Low", "Medium", "High"], index=["Low","Medium","High"].index(cur_priority) if cur_priority in ["Low","Medium","High"] else 1)
            category_new = st.text_input("Category", value=cur_category if cur_category else "General")
            # Update button
            if st.button("Update Task"):
                new_iso = parse_datetime_to_iso(due_date_new, due_time_new)
                ok = update_task(task_id_to_update, user,
                                 title=title_new.strip(), description=desc_new.strip(),
                                 due_iso=new_iso, priority=priority_new, category=category_new.strip())
                if ok:
                    st.success("Task updated ✅")
                    # clear fetched_task so next time user fetches afresh
                    if "fetched_task" in st.session_state:
                        del st.session_state["fetched_task"]
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error("Update failed.")
        else:
            st.info("Enter a Task ID and click 'Fetch Task' to load current values.")
    else:
        st.info("Only Admin/Manager can update tasks.")

# --------------------------
# ASK FOLLOW-UP QUESTION
# --------------------------
elif menu == "Ask Follow-up Question":
    st.subheader("💬 Ask Follow-up Question")
    task_id_for_q = st.number_input("Task ID", min_value=1, step=1, key="q_id")
    st.markdown("Enter your question/comment (cannot be empty):")
    comment_text = st.text_area("Question / Comment")
    if st.button("Submit Question"):
        if not comment_text or comment_text.strip() == "":
            st.error("Comment cannot be empty.")
        else:
            ok = add_comment(task_id_for_q, user[0], comment_text)
            if ok:
                st.success(f"Your question for Task {task_id_for_q} was submitted ✅")
                time.sleep(2)
                st.rerun()
            else:
                st.error("Invalid Task ID or error saving comment.")
    # Show recent comments for a valid Task ID
    if task_id_for_q:
        comments_list = get_comments(task_id_for_q)
        if comments_list:
            st.markdown("**Recent comments for this task:**")
            for c in comments_list:
                # c = (comment, username, timestamp)
                st.write(f"- **{c[1]}** ({c[2]}): {c[0]}")
        else:
            st.info("No comments for this Task ID (or invalid Task ID).")

# --------------------------
# LOGOUT
# --------------------------
elif menu == "Logout":
    st.session_state.clear()
    st.success("You have been logged out.")
    time.sleep(2)
    st.rerun()
