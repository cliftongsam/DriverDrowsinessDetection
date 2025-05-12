import ttkbootstrap as ttk # Enhanced ttk UI framework
from ttkbootstrap.constants import *
from tkinter import messagebox
import pymysql # MySQL connector
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from datetime import datetime
from PIL import Image, ImageTk
import time

# Store currently logged-in user's info (used globally)
logged_in_user = {"UserID": None, "Role": None}

# Connect to MySQL database
def create_connection():
    try:
        conn = pymysql.connect(
            host="127.0.0.1",
            user="drowsiness_user",
            password="DrowsinessPass4969!",
            database="drowsiness_main_db"
        )
        return conn
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        return None

# Authenticate login credentials against the User table
def authenticate_user(user_id, password):
    conn = create_connection()
    if conn is None:
        return False

    cursor = conn.cursor()
    cursor.execute("SELECT UserID, Role FROM User WHERE UserID = %s AND password = %s", (user_id, password))
    user = cursor.fetchone()
    conn.close()

    if user:
        logged_in_user["UserID"] = user[0]
        logged_in_user["Role"] = user[1]
        return True
    return False

# Load users and incidents from the database (filtered by role)
def fetch_data():
    try:
        conn = create_connection()
        if conn is None:
            return [], []

        cursor = conn.cursor()
        if logged_in_user["Role"] == "Admin":
            cursor.execute("SELECT UserID, DriverID, FirstName, LastName, Role FROM User")
        else:
            cursor.execute("SELECT UserID, DriverID, FirstName, LastName, Role FROM User WHERE UserID = %s",
                           (logged_in_user["UserID"],))
        users = cursor.fetchall()

        if logged_in_user["Role"] == "Admin":
            cursor.execute("SELECT IncidentID, UserID, Timestamp, EventType, VideoPath FROM Incident")
        else:
            cursor.execute("SELECT IncidentID, UserID, Timestamp, EventType, VideoPath FROM Incident WHERE UserID = %s",
                           (logged_in_user["UserID"],))
        incidents = cursor.fetchall()

        conn.close()
        return users, incidents
    except Exception as e:
        print(f"Error fetching data: {e}")
        return [], []

# Refresh treeview widgets with latest data
def update_gui():
    for item in tree_users.get_children():
        tree_users.delete(item)
    for item in tree_incidents.get_children():
        tree_incidents.delete(item)

    users, incidents = fetch_data()

    for user in users:
        tree_users.insert("", "end", values=user)
    for incident in incidents:
        tree_incidents.insert("", "end", values=incident)

# Periodic refresh every 10 seconds
def auto_refresh():
    update_gui()
    root.after(10000, auto_refresh)

# Login button callback
def login():
    user_id = user_id_entry.get()
    password = password_entry.get()

    try:
        user_id = int(user_id)
    except ValueError:
        messagebox.showerror("Error", "UserID must be a number")
        return

    # Attempt authentication
    if authenticate_user(user_id, password):
        login_frame.destroy()
        bg_label.destroy()
        title.destroy()
        show_main_gui()
    else:
        messagebox.showerror("Error", "Invalid UserID or Password")

# Logout and reset to login screen
def logout():
    global logged_in_user
    logged_in_user = {"UserID": None, "Role": None}
    for widget in root.winfo_children():
        widget.destroy()
    show_login_gui()

# Display the main dashboard interface based on user role
def show_main_gui():
    global tree_users, tree_incidents, search_user_entry, search_incident_entry

    top_button_frame = ttk.Frame(root)
    top_button_frame.pack(fill="x", padx=10, pady=10, anchor="ne")
    btn_style = {"bootstyle": "secondary", "padding": (10, 5)}

    ttk.Button(top_button_frame, text="Trend Analysis", command=show_trend_analysis, **btn_style).pack(side="right",
                                                                                                       padx=5)
    ttk.Button(top_button_frame, text="Logout", command=logout, **btn_style).pack(side="right", padx=5)
    ttk.Button(top_button_frame, text="Refresh", command=update_gui, **btn_style).pack(side="right", padx=5)
    
    # User Table 
    user_frame = ttk.LabelFrame(root, text="Users", padding=10)
    user_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Search users
    search_user_frame = ttk.Frame(user_frame)
    search_user_frame.pack(fill="x", pady=5)
    ttk.Label(search_user_frame, text="Search User:").pack(side="left", padx=5)
    search_user_entry = ttk.Entry(search_user_frame)
    search_user_entry.pack(side="left", fill="x", expand=True, padx=5)
    ttk.Button(search_user_frame, text="Search", command=search_users, bootstyle="primary").pack(side="left", padx=5)
    
    # User treeview
    tree_users = ttk.Treeview(user_frame, columns=("UserID", "DriverID", "FirstName", "LastName", "Role"), show="headings", height=5)
    for col in tree_users["columns"]:
        tree_users.heading(col, text=col)
    tree_users.pack(fill="both", expand=True)
    
    # Admin-only buttons: Add, Edit, Delete
    if logged_in_user["Role"] == "Admin":
        button_frame = ttk.Frame(user_frame)
        button_frame.pack(pady=5)
        ttk.Button(button_frame, text="Add User", command=add_user, bootstyle="secondary").pack(side="left", padx=5)
        ttk.Button(button_frame, text="Edit User",
                   command=lambda: edit_user(tree_users.item(tree_users.selection())['values']),
                   bootstyle="secondary").pack(side="left", padx=5)
        ttk.Button(button_frame, text="Delete User",
                   command=lambda: delete_user(tree_users.item(tree_users.selection())['values'][0]),
                   bootstyle="secondary").pack(side="left", padx=5)

    # Incident Table
    incident_frame = ttk.LabelFrame(root, text="Incidents", padding=10)
    incident_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Search incidents
    search_incident_frame = ttk.Frame(incident_frame)
    search_incident_frame.pack(fill="x", pady=5)
    ttk.Label(search_incident_frame, text="Search Incident:").pack(side="left", padx=5)
    search_incident_entry = ttk.Entry(search_incident_frame)
    search_incident_entry.pack(side="left", fill="x", expand=True, padx=5)
    ttk.Button(search_incident_frame, text="Search", command=search_incidents, bootstyle="primary").pack(side="left", padx=5)

    # Incident treeview
    tree_incidents = ttk.Treeview(incident_frame, columns=("IncidentID", "UserID", "Timestamp", "EventType", "VideoPath"), show="headings", height=5)
    for col in tree_incidents["columns"]:
        tree_incidents.heading(col, text=col)
    tree_incidents.pack(fill="both", expand=True)
    tree_incidents.bind("<Double-1>", show_incident_details)

    update_gui()
    root.after(10000, auto_refresh)


# Show login screen with background image
def show_login_gui():
    global login_frame, user_id_entry, password_entry, bg_label, title, original_bg

    # Class to handle background image resizing on window resize
    class BackgroundManager:
         def __init__(self):
             self.last_resize_time = 0
             try:
                 self.original_bg = Image.open("background.jpg")
                 print("Background image loaded successfully")
             except Exception as e:
                 print("Failed to load background image:", e)
                 self.original_bg = None

         def resize_bg(self, event=None):
             current_time = time.time()
             if current_time - self.last_resize_time < 0.1:
                 return
             self.last_resize_time = current_time

             if self.original_bg:
                 try:
                     resized = self.original_bg.resize((root.winfo_width(), root.winfo_height()))
                     bg_img = ImageTk.PhotoImage(resized)
                     bg_label.config(image=bg_img)
                     bg_label.image = bg_img
                 except Exception as e:
                     print("Error resizing background:", e)

    # Initialize background manager
    bg_manager = BackgroundManager()
    original_bg = bg_manager.original_bg

    # Create background label
    bg_label = ttk.Label(root)
    bg_label.place(x=0, y=0, relwidth=1, relheight=1)

    # Initial resize and bind the event
    #bg_manager.resize_bg()
    root.bind("<Configure>", bg_manager.resize_bg)

    # Heading
    title = ttk.Label(
         root,
         text="Driver Drowsiness Detection System",
         font=("Segoe UI", 28, "bold"),
         foreground="#4EA8DE",
         background="#000000",
         padding=15
     )
    title.place(relx=0.5, y=80, anchor="center")

    # Login Frame
    login_frame = ttk.Frame(root, bootstyle="dark")
    login_frame.place(relx=0.5, rely=0.55, anchor="center")

    form_title = ttk.Label(
        login_frame,
        text="Login",
        font=("Segoe UI", 16, "bold"),
        foreground="#4EA8DE",
        background="#1A1A1A",
        padding=(10, 5)
    )
    form_title.pack(pady=(0, 5))

     # Form content
    form = ttk.Frame(login_frame, padding=30)
    form.pack()
    input_width = 35
    ttk.Label(form, text="UserID:", font=("Segoe UI", 12)).pack(pady=(10, 5))
    user_id_entry = ttk.Entry(form, width=input_width)
    user_id_entry.pack(pady=(0, 15))
    ttk.Label(form, text="Password:", font=("Segoe UI", 12)).pack(pady=(5, 5))
    password_entry = ttk.Entry(form, show="*", width=input_width)
    password_entry.pack(pady=(0, 20))
    login_button = ttk.Button(form, text="Login", bootstyle="primary", width=25, command=login)
    login_button.pack(pady=10)
    print("Skipping remaining GUI elements for now")


# Admin: Add New User
def add_user():
    add_user_window = ttk.Toplevel(root)
    add_user_window.title("Add User")

    # Define fields for the form
    fields = ["DriverID", "First Name", "Last Name", "Role", "Password"]
    entries = []
    for i, label in enumerate(fields):
        ttk.Label(add_user_window, text=label + ":").grid(row=i, column=0, padx=5, pady=5)
        entry = ttk.Entry(add_user_window, show="*" if "Password" in label else "")
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries.append(entry)

    # Save new user to the database
    def save_user():
        data = [entry.get() for entry in entries]
        conn = create_connection()
        if conn is None: return
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO User (DriverID, FirstName, LastName, Role, password) VALUES (%s, %s, %s, %s, %s)", data)
            conn.commit()
            messagebox.showinfo("Success", "User added successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add user: {e}")
        finally:
            conn.close()
            add_user_window.destroy()
            update_gui()

    ttk.Button(add_user_window, text="Save", command=save_user, bootstyle="success").grid(row=len(fields), column=0, columnspan=2, pady=10)

# Admin: Edit Existing User
def edit_user(user_data):
    if not user_data:
        messagebox.showerror("Error", "No user selected")
        return

    edit_user_window = ttk.Toplevel(root)
    edit_user_window.title("Edit User")

    fields = ["DriverID", "First Name", "Last Name", "Role", "Password"]
    default_values = list(user_data[1:]) + [""]  

    entries = []
    for i, (label, value) in enumerate(zip(fields, default_values)):
        ttk.Label(edit_user_window, text=label + ":").grid(row=i, column=0, padx=5, pady=5)
        entry = ttk.Entry(edit_user_window, show="*" if "Password" in label else "")
        entry.insert(0, value)
        entry.grid(row=i, column=1, padx=5, pady=5)
        entries.append(entry)

    # Save updated user data
    def save_changes():
        driver_id = entries[0].get()
        first_name = entries[1].get()
        last_name = entries[2].get()
        role = entries[3].get()
        password = entries[4].get()

        conn = create_connection()
        if conn is None:
            return

        cursor = conn.cursor()
        try:
            if password.strip():  # Update password only if not empty
                cursor.execute("""
                    UPDATE User SET DriverID = %s, FirstName = %s, LastName = %s, Role = %s, password = %s WHERE UserID = %s
                """, (driver_id, first_name, last_name, role, password, user_data[0]))
            else:  # Keep old password
                cursor.execute("""
                    UPDATE User SET DriverID = %s, FirstName = %s, LastName = %s, Role = %s WHERE UserID = %s
                """, (driver_id, first_name, last_name, role, user_data[0]))

            conn.commit()
            messagebox.showinfo("Success", "User updated successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update user: {e}")
        finally:
            conn.close()
            edit_user_window.destroy()
            update_gui()

    ttk.Button(edit_user_window, text="Save", command=save_changes, bootstyle="success").grid(row=len(fields), column=0, columnspan=2, pady=10)

# Admin: Delete User
def delete_user(user_id):
    if messagebox.askyesno("Confirm", "Are you sure you want to delete this user?"):
        conn = create_connection()
        if conn is None: return
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM User WHERE UserID = %s", (user_id,))
            conn.commit()
            messagebox.showinfo("Success", "User deleted successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete user: {e}")
        finally:
            conn.close()
            update_gui()

# Search users based on user input
def search_users():
    term = search_user_entry.get()
    conn = create_connection()
    if conn is None: return
    cursor = conn.cursor()

    if logged_in_user["Role"] == "Admin":
        cursor.execute("""
            SELECT UserID, DriverID, FirstName, LastName, Role 
            FROM User 
            WHERE UserID LIKE %s OR DriverID LIKE %s OR FirstName LIKE %s OR LastName LIKE %s OR Role LIKE %s
        """, [f"%{term}%"] * 5)
    else:
        cursor.execute("""
            SELECT UserID, DriverID, FirstName, LastName, Role 
            FROM User 
            WHERE UserID = %s
        """, (logged_in_user["UserID"],))

    users = cursor.fetchall()
    conn.close()

    for item in tree_users.get_children():
        tree_users.delete(item)
    for user in users:
        tree_users.insert("", "end", values=user)

# Search incidents based on event type, ID, etc.
def search_incidents():
    term = search_incident_entry.get()
    conn = create_connection()
    if conn is None: return
    cursor = conn.cursor()

    if logged_in_user["Role"] == "Admin":
        cursor.execute("""
            SELECT IncidentID, UserID, Timestamp, EventType, VideoPath 
            FROM Incident 
            WHERE IncidentID LIKE %s OR UserID LIKE %s OR EventType LIKE %s
        """, [f"%{term}%"] * 3)
    else:
        cursor.execute("""
            SELECT IncidentID, UserID, Timestamp, EventType, VideoPath 
            FROM Incident 
            WHERE (IncidentID LIKE %s OR EventType LIKE %s) AND UserID = %s
        """, [f"%{term}%", f"%{term}%", logged_in_user["UserID"]])

    incidents = cursor.fetchall()
    conn.close()

    for item in tree_incidents.get_children():
        tree_incidents.delete(item)
    for incident in incidents:
        tree_incidents.insert("", "end", values=incident)


# Show detailed info about a double-clicked incident
def show_incident_details(event):
    selected_item = tree_incidents.selection()
    if selected_item:
        data = tree_incidents.item(selected_item)['values']
        detail_window = ttk.Toplevel(root)
        detail_window.title("Incident Details")
        for i, label in enumerate(["IncidentID", "UserID", "Timestamp", "EventType", "VideoPath"]):
            ttk.Label(detail_window, text=f"{label}: {data[i]}").pack(pady=5)


def show_trend_analysis():
    import pandas as pd
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

    # --- Color Theme ---
    BG_COLOR = "#000000"
    CARD_COLOR = "#121212"
    TEXT_COLOR = "#E0E1DD"
    ACCENT_COLORS = ["#4EA8DE", "#27AE60", "#9B59B6", "#F39C12"]

    # Fetch Incident Data from DB
    def fetch_incident_data(user_id=None):
        conn = create_connection()
        if conn is None:
            return []
        cursor = conn.cursor()
        # Admin can view all or filtered by user
        if logged_in_user["Role"] == "Admin":
            if user_id:
                cursor.execute("SELECT Timestamp, EventType FROM Incident WHERE UserID = %s", (user_id,))
            else:
                cursor.execute("SELECT Timestamp, EventType FROM Incident")
        else:
            # Driver can only view their own incidents
            cursor.execute("SELECT Timestamp, EventType FROM Incident WHERE UserID = %s", (logged_in_user["UserID"],))
        incidents = cursor.fetchall()
        conn.close()
        return incidents

    # Analyze & Plot Data
    def refresh_analysis(user_id=None):
        incidents = fetch_incident_data(user_id)
        if not incidents:
            messagebox.showinfo("Info", "No incident data available.")
            return
        
        # Create DataFrame and extract useful features
        df = pd.DataFrame({
            "Timestamp": [i[0] for i in incidents],
            "EventType": [i[1] for i in incidents]
        })
        df["Date"] = df["Timestamp"].dt.date
        df["Day"] = df["Timestamp"].dt.day_name()

        daily_counts = df.groupby("Date")["EventType"].count()
        type_counts = df["EventType"].value_counts()
        day_counts = df["Day"].value_counts().reindex(
            ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            fill_value=0
        )

        for tab in notebook.tabs():
            notebook.forget(tab)

        plt.style.use("dark_background")

        # Tab 1: Daily Trends Line Chart
        tab1 = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(tab1, text="Daily Trends")
        fig1, ax1 = plt.subplots(figsize=(6, 4), facecolor=CARD_COLOR)
        ax1.plot(daily_counts.index, daily_counts.values, marker='o', color=ACCENT_COLORS[0], linewidth=2)
        ax1.set_title("Daily Incident Trends", color=TEXT_COLOR)
        ax1.set_xlabel("Date", color=TEXT_COLOR)
        ax1.set_ylabel("Incident Count", color=TEXT_COLOR)
        ax1.tick_params(colors=TEXT_COLOR)
        ax1.set_facecolor(CARD_COLOR)
        ax1.grid(color="#333333", linestyle="--", alpha=0.3)
        plt.setp(ax1.get_xticklabels(), rotation=45, ha="right")
        fig1.tight_layout()
        canvas1 = FigureCanvasTkAgg(fig1, master=tab1)
        canvas1.draw()
        canvas1.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 2: Event Types (Bar + Pie)
        tab2 = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(tab2, text=" Event Types")
        fig2, axs = plt.subplots(1, 2, figsize=(8, 4), facecolor=CARD_COLOR)

        # Bar chart with smaller bar width
        bars = axs[0].bar(type_counts.index, type_counts.values, color=ACCENT_COLORS[1], width=0.4)
        axs[0].set_title("Event Type Count", color=TEXT_COLOR)
        axs[0].tick_params(colors=TEXT_COLOR)
        axs[0].set_facecolor(CARD_COLOR)
        axs[0].grid(color="#333333", linestyle="--", axis="y", alpha=0.3)
        for bar in bars:
            axs[0].text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                        f'{int(bar.get_height())}', ha='center', va='bottom', color=TEXT_COLOR, fontsize=9)

        # Pie chart
        axs[1].pie(type_counts.values,
                   labels=type_counts.index,
                   autopct='%1.1f%%',
                   colors=ACCENT_COLORS,
                   textprops={'color': TEXT_COLOR},
                   wedgeprops={'edgecolor': CARD_COLOR})
        axs[1].set_title("Event Proportions", color=TEXT_COLOR)
        fig2.tight_layout()
        canvas2 = FigureCanvasTkAgg(fig2, master=tab2)
        canvas2.draw()
        canvas2.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 3: Weekly Pattern (Bar Chart)
        tab3 = ttk.Frame(notebook, style="Card.TFrame")
        notebook.add(tab3, text=" Weekly Pattern")
        fig3, ax3 = plt.subplots(figsize=(6, 4), facecolor=CARD_COLOR)
        bars_day = ax3.bar(day_counts.index, day_counts.values, color=ACCENT_COLORS[2], width=0.5)
        ax3.set_title("Weekly Pattern", color=TEXT_COLOR)
        ax3.set_ylabel("Count", color=TEXT_COLOR)
        ax3.tick_params(colors=TEXT_COLOR)
        ax3.set_facecolor(CARD_COLOR)
        ax3.grid(color="#444444", linestyle="--", axis="y", alpha=0.3)
        for bar in bars_day:
            ax3.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                     str(int(bar.get_height())), ha='center', va='bottom', color=TEXT_COLOR, fontsize=9)
        plt.setp(ax3.get_xticklabels(), rotation=45, ha="right")
        fig3.tight_layout()
        canvas3 = FigureCanvasTkAgg(fig3, master=tab3)
        canvas3.draw()
        canvas3.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # Create Trend Window
    trend_window = ttk.Toplevel(root)
    trend_window.title("Drowsiness Trend Analysis")
    trend_window.geometry("1100x700")
    trend_window.configure(background=BG_COLOR)

    # Style settings for dark theme
    style = ttk.Style()
    style.configure("Card.TFrame", background=BG_COLOR)
    style.configure("TLabel", background=BG_COLOR, foreground=TEXT_COLOR)
    style.configure("TButton", background="#222222", foreground=TEXT_COLOR)
    style.configure("TCombobox", fieldbackground="#1B263B", foreground=TEXT_COLOR)

    main_container = ttk.Frame(trend_window, style="Card.TFrame")
    main_container.pack(fill="both", expand=True)

    # Admin Driver Filter Dropdown
    selected_user_id = None
    if logged_in_user["Role"] == "Admin":
        top_frame = ttk.Frame(main_container, style="Card.TFrame")
        top_frame.pack(fill="x", padx=15, pady=(15, 5))
        ttk.Label(top_frame, text="Select Driver:", style="TLabel").pack(side="left", padx=(10, 5))

        user_combo = ttk.Combobox(top_frame, state="readonly", style="TCombobox")
        user_combo.pack(side="left", fill="x", expand=True, padx=5)

        conn = create_connection()
        user_map = {}
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT UserID, FirstName, LastName FROM User WHERE Role = 'Driver'")
            drivers = cursor.fetchall()
            user_map = {f"{first} {last} (ID: {uid})": uid for uid, first, last in drivers}
            user_map["All Users"] = None
            user_combo["values"] = list(user_map.keys())
            conn.close()

        # Dropdown event binding
        def on_driver_select(event=None):
            nonlocal selected_user_id
            selected_user_id = user_map.get(user_combo.get())
            refresh_analysis(user_id=selected_user_id)

        user_combo.bind("<<ComboboxSelected>>", on_driver_select)
        user_combo.set("All Users")

    # Create Notebook for Tabs
    notebook = ttk.Notebook(main_container)
    notebook.pack(fill="both", expand=True, padx=15, pady=15)

    # Close Button
    bottom_frame = ttk.Frame(main_container, style="Card.TFrame")
    bottom_frame.pack(fill="x", padx=15, pady=(0, 15))
    ttk.Button(bottom_frame, text="Close", command=trend_window.destroy, style="TButton").pack(side="right")

    # Load Initial Analysis
    refresh_analysis()


# ----------------------------
# Start GUI
# ----------------------------
root = ttk.Window(themename="cyborg")
style = ttk.Style()

# Treeview (Tables)
style.configure('Treeview',
    background='#1E1E2F',
    fieldbackground='#1E1E2F',
    foreground='#E0E0E0',
    bordercolor="#4EA8DE",
    font=('Segoe UI', 10)
)
style.configure('Treeview.Heading',
    background='#121212',
    foreground='#4EA8DE',
    font=('Segoe UI', 10, 'bold')
)

# LabelFrame (Section Frames)
style.configure('TLabelframe', background='#121212', bordercolor='#4EA8DE')
style.configure('TLabelframe.Label', foreground='#4EA8DE', font=('Segoe UI', 11, 'bold'))

# Entry (Text Input)
style.configure('TEntry',
    fieldbackground='#1E1E2F',
    foreground='#E0E0E0',
    insertcolor='white',
    font=('Segoe UI', 10)
)

# Label (Text)
style.configure('TLabel',
    background='#121212',
    foreground='#E0E0E0',
    font=('Segoe UI', 10)
)

root.title("Drowsiness Detection System")
root.geometry("1000x700")

show_login_gui()
root.mainloop()
