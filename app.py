import streamlit as st
import sqlite3
import pandas as pd
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
    return cur.fetchone()  # None if not found

def get_tasks(user_id=None, role=None):
    if role in ["Admin","Manager"]:
        cur.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks")
    else:
        cur.execute("SELECT task_id, title, description, due_date, status, priority, category, assigned_to FROM Tasks WHERE assigned_to=?", (user_id,))
    return cur.fetchall()

def add_task(assign_to, title, description, due_date, priority, category):
    cur.execute("""
        INSERT INTO Tasks (assigned_to, title, description, due_date, status, priority, category)
        VALUES (?,?,?,?,?,?,?)
    """, (assign_to, title, description, due_date, "Pending", priority, category))
    conn.commit()

def update_task_status(task_id, status):
    cur.execute("UPDATE Tasks SET status=? WHERE task_id=?", (status, task_id))
    conn.commit()

def add_comment(task_id, user_id, comment):
    cur.execute("INSERT INTO Comments (task_id, user_id, comment, timestamp) VALUES (?,?,?,?)", (task_id, user_id, comment, datetime.now()))
    conn.commit()

def get_comments(task_id):
    cur.execute("SELECT u.username, c.comment, c.timestamp FROM Comments c JOIN Users u ON c.user_id=u.user_id WHERE c.task_id=? ORDER BY c.timestamp DESC", (task_id,))
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
            st.experimental_rerun()  # refresh app after login
        else:
            st.error("Invalid credentials")

else:
    user = st.session_state.user
    st.sidebar.write(f"Logged in as: {user[1]} ({user[3]})")

    # Logout button
    if st.sidebar.button("Logout"):
        for key in st.session_state.keys():
            del st.session_state[key]
        st.success("Logged out successfully!")
        st.stop()

    # Sidebar Menu
    choice = st.sidebar.selectbox("Menu", ["📋 All Tasks", "⚠️ Overdue & Due Soon", "➕ Create Task"])

    # --------------------------
    # All Tasks
    # --------------------------
    if choice == "📋 All Tasks":
        st.subheader("All Tasks")
        tasks = get_tasks(user_id=user[0], role=user[3])
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

                    # Mark as completed if assigned to user
                    if t[7] == user[0] and t[4] != "Completed":
                        if st.button("Mark as Completed ✅", key=f"complete_{t[0]}"):
                            update_task_status(t[0], "Completed")
                            st.success("Task marked as Completed ✅")
                            st.experimental_rerun()

                    # Comments
                    st.subheader("Comments")
                    comments = get_comments(t[0])
                    if comments:
                        for c in comments:
                            st.write(f"{c[0]} ({c[2]}): {c[1]}")
                    else:
                        st.write("No comments yet.")

                    # Add Comment
                    comment_text = st.text_area("Add Comment", key=f"comment_{t[0]}")
                    if st.button("Post Comment", key=f"post_{t[0]}"):
                        if comment_text.strip() != "":
                            add_comment(t[0], user[0], comment_text)
                            st.success("Comment added!")
                            st.experimental_rerun()
                        else:
                            st.warning("Cannot post empty comment.")

        else:
            st.info("No tasks found.")

    # --------------------------
    # Overdue & Due Soon
    # --------------------------
    elif choice == "⚠️ Overdue & Due Soon":
        st.subheader("Overdue & Due Soon")
        now = datetime.now()
        soon = now + timedelta(days=1)

        # Overdue Tasks
        st.write("**Overdue Tasks:**")
        cur.execute("SELECT task_id, title, due_date, status FROM Tasks WHERE due_date < ? AND status='Pending'", (now,))
        overdue = cur.fetchall()
        if overdue:
            df_overdue = pd.DataFrame(overdue, columns=["Task ID", "Title", "Due Date", "Status"])
            st.table(df_overdue.style.hide_index())
        else:
            st.info("No overdue tasks.")

        # Due in next 24 hours
        st.write("**Tasks Due in Next 24 Hours:**")
        cur.execute("SELECT task_id, title, due_date, status FROM Tasks WHERE due_date BETWEEN ? AND ? AND status='Pending'", (now, soon))
        due_soon = cur.fetchall()
        if due_soon:
            df_due = pd.DataFrame(due_soon, columns=["Task ID", "Title", "Due Date", "Status"])
            st.table(df_due.style.hide_index())
        else:
            st.info("No tasks due in next 24 hours.")

    # --------------------------
    # Create Task
    # --------------------------
    elif choice == "➕ Create Task":
        st.subheader("Add Task")
        if user[3] in ["Admin", "Manager"]:
            title = st.text_input("Title")
            description = st.text_area("Description")
            due_date = st.date_input("Due Date")
            priority = st.selectbox("Priority", ["Low","Medium","High"])
            category = st.selectbox("Category", ["General", "Reporting", "Development", "Research"])
            assign_to = st.number_input("Assign to Employee ID", min_value=1, step=1)

            if st.button("Add Task"):
                add_task(assign_to, title, description, due_date, priority, category)
                st.success("Task added successfully!")
        else:
            st.info("Only Admin or Manager can create tasks.")
