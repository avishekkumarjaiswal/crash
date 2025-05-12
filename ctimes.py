import streamlit as st
import sqlite3
import random
import time
import pandas as pd
import plotly.graph_objects as go
import hashlib
from datetime import datetime

# Set up the Streamlit page (must be the first command)
st.set_page_config(layout="wide")  # Use the full width of the screen

# Hide Streamlit menu, footer, and prevent code inspection
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display: none !important;}  /* Hide GitHub button */
    </style>

    <script>
    document.addEventListener('contextmenu', event => event.preventDefault());
    document.onkeydown = function(e) {
        if (e.ctrlKey && (e.keyCode === 85 || e.keyCode === 83)) {
            return false;  // Disable "Ctrl + U" (View Source) & "Ctrl + S" (Save As)
        }
        if (e.keyCode == 123) {
            return false;  // Disable "F12" (DevTools)
        }
    };
    </script>
    """, unsafe_allow_html=True)

# Custom CSS for better styling
st.markdown(
    """
    <style>
    /* General Styling */
    body {
        font-family: 'Arial', sans-serif;
        background-color: #f5f5f5;
    }
    @keyframes slide {
        0% { transform: translateX(0%); }
        100% { transform: translateX(-100%); }
    }
    /* Popup CSS */
    .popup {
        position: fixed;
        top: 20px;
        right: 20px;
        background-color: #4CAF50;
        color: white;
        padding: 15px;
        border-radius: 5px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        z-index: 1000;
        animation: fadeInOut 3s ease-in-out;
    }
    @keyframes fadeInOut {
        0% { opacity: 0; }
        10% { opacity: 1; }
        90% { opacity: 1; }
        100% { opacity: 0; }
    }
    .admin-button {
        background-color: #dc3545 !important;
        color: white !important;
        border: none !important;
    }
    .user-button {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Password Hashing ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- Database Functions ---
def init_db():
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    
    # Users table with password and admin flag
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            balance REAL DEFAULT 10000.0,
            rounds_played INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT
        )
    ''')
    
    # Bets table
    c.execute('''
        CREATE TABLE IF NOT EXISTS bets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            bet_amount REAL,
            cashout_multiplier REAL,
            win_amount REAL,
            crash_multiplier REAL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create default admin if not exists
    admin_password = hash_password("admin123")
    c.execute('''
        INSERT OR IGNORE INTO users (username, password, is_admin, balance) 
        VALUES (?, ?, 1, 100000)
    ''', ("admin", admin_password))
    
    conn.commit()
    conn.close()

def add_user(username, password, is_admin=False):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    try:
        c.execute('''
            INSERT INTO users (username, password, is_admin) 
            VALUES (?, ?, ?)
        ''', (username, hashed_password, 1 if is_admin else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Username already exists
    except Exception as e:
        print(f"An error occurred: {e}")  # Optional: log the error
        return False
    finally:
        conn.close()  # Ensure the connection is closed

def verify_user(username, password):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    hashed_password = hash_password(password)
    c.execute('''
        SELECT * FROM users 
        WHERE username=? AND password=?
    ''', (username, hashed_password))
    user = c.fetchone()
    conn.close()
    return user

def get_user(username):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username=?', (username,))
    user = c.fetchone()
    conn.close()
    return user

def update_user_password(username, new_password):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    hashed_password = hash_password(new_password)
    c.execute('''
        UPDATE users 
        SET password = ? 
        WHERE username=?
    ''', (hashed_password, username))
    conn.commit()
    conn.close()

def update_balance(username, amount):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET balance = balance + ? 
        WHERE username=?
    ''', (amount, username))
    conn.commit()
    conn.close()

def add_bet(username, bet_amount, cashout_multiplier, win_amount, crash_multiplier):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO bets (username, bet_amount, cashout_multiplier, win_amount, crash_multiplier) 
        VALUES (?, ?, ?, ?, ?)
    ''', (username, bet_amount, cashout_multiplier, win_amount, crash_multiplier))
    conn.commit()
    conn.close()

def get_bets(limit=50, username=None):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    if username:
        c.execute('''
            SELECT username, bet_amount, cashout_multiplier, win_amount, crash_multiplier, timestamp 
            FROM bets 
            WHERE username=? 
            ORDER BY id DESC 
            LIMIT ?
        ''', (username, limit))
    else:
        c.execute('''
            SELECT username, bet_amount, cashout_multiplier, win_amount, crash_multiplier, timestamp 
            FROM bets 
            ORDER BY id DESC 
            LIMIT ?
        ''', (limit,))
    bets = c.fetchall()
    conn.close()
    return bets

def get_all_users():
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('''
        SELECT id, username, balance, rounds_played, is_admin, created_at, last_login 
        FROM users 
        ORDER BY balance DESC
    ''')
    users = c.fetchall()
    conn.close()
    return users

def delete_user(username):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE username=?', (username,))
    c.execute('DELETE FROM bets WHERE username=?', (username,))
    conn.commit()
    conn.close()

def update_user_balance(username, new_balance):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET balance = ? 
        WHERE username=?
    ''', (new_balance, username))
    conn.commit()
    conn.close()

def update_last_login(username):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET last_login = ? 
        WHERE username=?
    ''', (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username))
    conn.commit()
    conn.close()

def get_rounds_played(username):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM bets WHERE username=?', (username,))
    rounds_played = c.fetchone()[0]
    conn.close()
    return rounds_played

def get_total_bets(username):
    conn = sqlite3.connect('crash_game_secure.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM bets WHERE username=?', (username,))
    total_bets = c.fetchone()[0]  # Return the count of bets
    conn.close()
    return total_bets

# --- Initialize Database ---
init_db()

# --- Session State Setup ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'playing' not in st.session_state:
    st.session_state.playing = False
if 'progress' not in st.session_state:
    st.session_state.progress = 1.0
if 'crash_multiplier' not in st.session_state:
    st.session_state.crash_multiplier = 0.0
if 'bet_amount' not in st.session_state:
    st.session_state.bet_amount = 0.0
if 'start_time' not in st.session_state:
    st.session_state.start_time = 0.0
if 'auto_cashout' not in st.session_state:
    st.session_state.auto_cashout = None
if 'show_password_change' not in st.session_state:
    st.session_state.show_password_change = False
if 'show_admin_panel' not in st.session_state:
    st.session_state.show_admin_panel = False
if 'show_user_management' not in st.session_state:
    st.session_state.show_user_management = False

# --- Sidebar: Login ---
st.sidebar.title("🚀 Crash Game Authentication")

if not st.session_state.logged_in:
    login_tab, register_tab = st.sidebar.tabs(["Login", "Register"])
    
    with login_tab:
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        
        if st.button("Login"):
            user = verify_user(username_input, password_input)
            if user:
                st.session_state.username = user[1]
                st.session_state.logged_in = True
                st.session_state.is_admin = bool(user[5])
                update_last_login(st.session_state.username)
                st.sidebar.success(f"Welcome back, {st.session_state.username}!")
            st.rerun()
    
    with register_tab:
        new_username = st.text_input("Choose Username")
        new_password = st.text_input("Choose Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        
        if st.button("Create Account"):
            if new_password != confirm_password:
                st.error("Passwords don't match!")
            elif len(new_password) < 6:
                st.error("Password must be at least 6 characters")
            elif len(new_username) < 3:
                st.error("Username must be at least 3 characters")
            else:
                if add_user(new_username, new_password):
                    st.success("Account created successfully! Please login.")
                else:
                    st.error("Username already exists")

else:
    # Display logged-in user info
    user = get_user(st.session_state.username)
    if user:  # Check if user exists
        user_balance = user[3]
        total_bets = get_total_bets(st.session_state.username)  # Get total number of bets for the user

        st.sidebar.markdown(f"<h2 style='color: #007bff;'>👤 {st.session_state.username}</h2>", unsafe_allow_html=True)
        
        if st.session_state.is_admin:
            st.sidebar.markdown("<h3 style='color: #dc3545;'>ADMIN ACCOUNT</h3>", unsafe_allow_html=True)
        else:
            st.sidebar.markdown(f"<h4>Balance: ₹{user_balance:.2f}</h4>", unsafe_allow_html=True)

            # Calculate and display the user's rank
            users = get_all_users()  # Get all users to determine rank
            leaderboard_data = []
            for user in users:
                if not user[4]:  # Check if the user is not an admin
                    total_bets_user = get_total_bets(user[1])  # Get total number of bets for the user
                    leaderboard_data.append({
                        "Username": user[1],
                        "Total Bets": total_bets_user,
                    })

            # Assign ranks starting from 1
            for rank, user in enumerate(leaderboard_data, start=1):
                user["Rank"] = rank

            # Find the user's rank
            user_rank = next((u["Rank"] for u in leaderboard_data if u["Username"] == st.session_state.username), None)

            # Display the user's rank below the balance
            if user_rank is not None:
                st.sidebar.markdown(f"<h4>Rank: {user_rank}</h4>", unsafe_allow_html=True)

        # Password change section
        if st.sidebar.button("Change Password"):
            st.session_state.show_password_change = not st.session_state.show_password_change
        
        if st.session_state.show_password_change:
            with st.sidebar.form("password_change_form"):
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Update Password"):
                    if new_password != confirm_new_password:
                        st.error("New passwords don't match!")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        # Verify current password first
                        if verify_user(st.session_state.username, current_password):
                            update_user_password(st.session_state.username, new_password)
                            st.success("Password updated successfully!")
                            st.session_state.show_password_change = False
                            st.rerun()
                        else:
                            st.error("Current password is incorrect")
        
        # Admin panel toggle
        if st.session_state.is_admin:
            if st.sidebar.button("Admin Panel", key="admin_panel_toggle"):
                st.session_state.show_admin_panel = not st.session_state.show_admin_panel
        
        # Logout button
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
            st.session_state.logged_in = False
        st.rerun()

# --- Main Interface ---
if st.session_state.logged_in:
    # Admin Panel
    if st.session_state.is_admin and st.session_state.show_admin_panel:
        st.title("🛠️ Admin Panel")
        
        admin_tabs = st.tabs(["User Management", "Game Statistics", "System Settings"])
        
        with admin_tabs[0]:
            st.subheader("User Accounts Management")
            
            # Create new user (admin only)
            with st.expander("Create New User"):
                with st.form("create_user_form"):
                    new_username = st.text_input("Username")
                    new_password = st.text_input("Password", type="password")
                    is_admin = st.checkbox("Admin Privileges")
                    if not is_admin:
                        initial_balance = st.number_input("Initial Balance", min_value=0.0, value=10000.0, step=1000.0)
                    else:
                        initial_balance = 0.0
                    
                    if st.form_submit_button("Create User"):
                        if add_user(new_username, new_password, is_admin):
                            if not is_admin:
                                update_user_balance(new_username, initial_balance)
                            st.success(f"User {new_username} created successfully!")
                        else:
                            st.error("Username already exists")
            
            # User list with management options
            st.subheader("All Users")
            users = get_all_users()
            users_df = pd.DataFrame(users, columns=["ID", "Username", "Balance", "Rounds", "Is Admin", "Created At", "Last Login"])
            
            # Display editable dataframe
            edited_df = st.data_editor(
                users_df,
                column_config={
                    "Is Admin": st.column_config.CheckboxColumn("Is Admin"),
                    "Balance": st.column_config.NumberColumn("Balance", format="₹%.2f"),
                },
                hide_index=True,
                use_container_width=True,
                disabled=["ID", "Username", "Rounds", "Created At", "Last Login"]
            )
            
            # Apply changes button
            if st.button("Apply Changes"):
                for index, row in edited_df.iterrows():
                    # Update admin status and balance
                    original_user = users[index]
                    changes_made = False
                    
                    # Check if admin status changed
                    if bool(row["Is Admin"]) != bool(original_user[4]):
                        conn = sqlite3.connect('crash_game_secure.db')
                        c = conn.cursor()
                        c.execute('''
                            UPDATE users 
                            SET is_admin = ? 
                            WHERE id = ?
                        ''', (int(row["Is Admin"]), row["ID"]))
                        conn.commit()
                        conn.close()
                        changes_made = True
                    
                    # Check if balance changed
                    if float(row["Balance"]) != float(original_user[2]):
                        update_user_balance(row["Username"], row["Balance"])
                        changes_made = True
                    
                if changes_made:
                    st.success("Changes saved successfully!")
                    st.rerun()
                else:
                    st.info("No changes detected")
            
            # User deletion
            with st.expander("Delete User", expanded=False):
                user_to_delete = st.selectbox(
                    "Select user to delete",
                    [user[1] for user in users if user[1] != st.session_state.username],
                    index=0
                )
                
                if st.button("Delete User", key="delete_user_button"):
                    delete_user(user_to_delete)
                    st.success(f"User {user_to_delete} deleted successfully!")
                    st.rerun()
        
        with admin_tabs[1]:
            st.subheader("Game Statistics")
            
            # Total users
            conn = sqlite3.connect('crash_game_secure.db')
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM users')
            total_users = c.fetchone()[0]
            
            c.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
            total_admins = c.fetchone()[0]
            
            c.execute('SELECT SUM(balance) FROM users')
            total_balance = c.fetchone()[0] or 0
            
            c.execute('SELECT COUNT(*) FROM bets')
            total_bets = c.fetchone()[0]
            
            conn.close()
            
            # Display stats in columns
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Users", total_users)
            col2.metric("Administrators", total_admins)
            col3.metric("Total Balance", f"₹{total_balance:,.2f}")
            col4.metric("Total Bets Placed", total_bets)
            
            # Bet history chart
            st.subheader("Bet History")
            all_bets = get_bets(limit=1000)
            if all_bets:
                bet_dates = [datetime.strptime(row[5], "%Y-%m-%d %H:%M:%S").date() for row in all_bets]
                bet_amounts = [row[1] for row in all_bets]
                
                # Create a DataFrame with date and bet amount
                bets_by_date = pd.DataFrame({
                    'Date': bet_dates,
                    'Bet Amount': bet_amounts
                })
                
                # Group by date and sum bet amounts
                daily_bets = bets_by_date.groupby('Date').sum().reset_index()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=daily_bets['Date'],
                    y=daily_bets['Bet Amount'],
                    mode='lines+markers',
                    name='Daily Bet Volume'
                ))
                
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Total Bet Amount (₹)",
                    title="Daily Betting Activity",
                    height=400
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        with admin_tabs[2]:
            st.subheader("System Settings")
            
            # Database management
            with st.expander("Database Operations"):
                if st.button("Export Database Backup"):
                    # In a real app, you would implement proper backup functionality
                    st.warning("Backup functionality would be implemented in production")
                
                if st.button("Reset Demo Data"):
                    st.warning("This would reset all data in a real implementation")
                    st.info("Demo only - no action taken")
            
            # System information
            st.subheader("System Information")
            st.write(f"Database file: crash_game_secure.db")
            st.write(f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Main Game Interface (only show if admin panel is not shown or user is not admin)
    if not st.session_state.is_admin or not st.session_state.show_admin_panel:
        st.title("🚀 Crash Game")

    user = get_user(st.session_state.username)
    if user:  # Check if user exists
        balance = user[3]
        st.subheader(f"Balance: ₹{balance:.2f}")
    else:
        st.error("User not found. Please log in again.")

    # Initialize speed_factor
    speed_factor = 0.05  # Default to Easy speed

    # --- Tabs for navigation ---
    tabs = st.tabs(["🎮 Play Game", "📋 My Bets", "💵 Crash History", "🏆 Leaderboard"])

    # ----------------- Play Game Tab -----------------
    with tabs[0]:
        if not st.session_state.playing:
            with st.form(key="bet_form"):
                bet_amount = st.number_input("Enter Bet Amount", min_value=100.0, step=50.0, key="bet_amount_input")
                auto_cashout_input = st.text_input("Auto Cashout At (x) (Optional)", key="auto_cashout_input")
                submit = st.form_submit_button("Place Bet and Start")

                if submit:
                    if bet_amount > balance:
                        st.error("Insufficient Balance!")
                    else:
                        if auto_cashout_input.strip() == "":
                            st.session_state.auto_cashout = None
                        else:
                            try:
                                st.session_state.auto_cashout = float(auto_cashout_input)
                                if st.session_state.auto_cashout < 1.0:
                                    st.error("Auto Cashout must be at least 1.0x if set.")
                                    st.stop()
                            except:
                                st.error("Invalid Auto Cashout value. Enter a number like 2.5.")
                                st.stop()

                        st.session_state.bet_amount = bet_amount
                        
                        # --- Adjust crash_multiplier based on balance ---
                        if balance > 30000:
                            st.session_state.crash_multiplier = round(random.uniform(1.0, 2.0), 2)  # Low chance
                            speed_factor = 0.2  # Moderate speed
                        elif balance > 15000:
                            st.session_state.crash_multiplier = round(random.uniform(2.0, 4.0), 2)  # Moderate chance
                            speed_factor = 0.1  # Faster speed
                        else:  # High balance
                            st.session_state.crash_multiplier = round(random.uniform(4.0, 7.0), 2)  # Higher chance
                            speed_factor = 0.05  # Fastest speed
                        
                        st.session_state.progress = 1.0
                        st.session_state.playing = True
                        update_balance(st.session_state.username, -bet_amount)
                        st.success("Bet Placed! Game Started 🚀")
                        st.rerun()
        else:
            st.markdown("### 🎮 Game in progress...")
            placeholder = st.empty()
            with placeholder.container():
                st.markdown(f"<h1 style='text-align:center;color:green;'>{st.session_state.progress:.2f}x</h1>", unsafe_allow_html=True)
                take_win = st.button("🏆 TAKE WIN")

            if take_win:
                win_amount = st.session_state.bet_amount * st.session_state.progress
                update_balance(st.session_state.username, win_amount)
                add_bet(st.session_state.username, st.session_state.bet_amount, st.session_state.progress, win_amount, st.session_state.crash_multiplier)
                
                # Show winning message
                placeholder.markdown(f"<h1 style='color:green; text-align:center;'>Cashed out at {st.session_state.progress:.2f}x! Won ₹{win_amount:.2f}</h1>", unsafe_allow_html=True)
                st.session_state.playing = False
                
                # Wait for 2 second before resetting
                time.sleep(2)
                
                # Reset game state for a new bet
                st.session_state.progress = 1.0
                st.session_state.crash_multiplier = round(random.uniform(1.5, 7.0), 2)
                st.session_state.bet_amount = 0.0
                st.rerun()  # Rerun the app to start fresh

            elif st.session_state.progress >= st.session_state.crash_multiplier:
                # Show crash message
                placeholder.markdown(f"<h1 style='color:red; text-align:center;'>💥 Crashed at {st.session_state.crash_multiplier:.2f}x!</h1>", unsafe_allow_html=True)
                add_bet(st.session_state.username, st.session_state.bet_amount, st.session_state.progress, 0.0, st.session_state.crash_multiplier)
                st.error(f"You lost the bet! Crash occurred at {st.session_state.crash_multiplier:.2f}x.")
                st.session_state.playing = False
                
                # Wait for 2 second before showing the new bid button
                time.sleep(2)
                
                # Show button to start a new bid
                if st.button("Start New Bid"):
                    st.session_state.playing = False  # Reset playing state
                    st.session_state.progress = 1.0  # Reset progress
                    st.session_state.crash_multiplier = round(random.uniform(1.5, 7.0), 2)  # Reset crash multiplier
                    st.session_state.bet_amount = 0.0  # Reset bet amount
                    st.session_state.start_time = 0.0  # Reset start time
                    st.experimental_rerun()  # Rerun the app to start fresh

            elif st.session_state.auto_cashout is not None and st.session_state.progress >= st.session_state.auto_cashout:
                # Show auto cashout message
                placeholder.markdown(f"<h1 style='color:blue; text-align:center;'>Auto Cashed Out at {st.session_state.auto_cashout:.2f}x!</h1>", unsafe_allow_html=True)
                win_amount = st.session_state.bet_amount * st.session_state.auto_cashout
                update_balance(st.session_state.username, win_amount)
                add_bet(st.session_state.username, st.session_state.bet_amount, st.session_state.auto_cashout, win_amount, st.session_state.crash_multiplier)
                st.session_state.playing = False
                
                # Wait for 2 second before resetting
                time.sleep(2)
                
                # Reset game state for a new bet
                st.session_state.progress = 1.0
                st.session_state.crash_multiplier = round(random.uniform(1.5, 7.0), 2)
                st.session_state.bet_amount = 0.0
                st.rerun()  # Rerun the app to start fresh

            else:
                st.session_state.progress += speed_factor  # Update progress based on speed factor
                time.sleep(0.2)  # Adjust sleep time if necessary
                st.rerun()

        # ----------------- My Bets Tab -----------------
    with tabs[1]:
        bets = get_bets(limit=2000000000, username=st.session_state.username)
        if bets:
            st.subheader("📋 My Recent Bets")
            bets_df = pd.DataFrame(bets, columns=["Username", "Bet (₹)", "Cashout (x)", "Win (₹)", "Crash at (x)", "Time"])
            # Format the time column
            bets_df["Time"] = pd.to_datetime(bets_df["Time"]).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(
                bets_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Bet (₹)": st.column_config.NumberColumn(format="₹%.2f"),
                    "Win (₹)": st.column_config.NumberColumn(format="₹%.2f")
                }
            )
            
            # Calculate and display stats
            total_bets = len(bets)
            total_wagered = sum(bet[1] for bet in bets)
            total_won = sum(bet[3] for bet in bets)
            net_profit = total_won - total_wagered
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Bets", total_bets)
            col2.metric("Total Wagered", f"₹{total_wagered:,.2f}")
            col3.metric("Net Profit", f"₹{net_profit:,.2f}", delta_color="inverse")
        else:
            st.info("You haven't placed any bets yet")

    # ----------------- Crash History Tab -----------------
    with tabs[2]:
        all_bets = get_bets(limit=50)
        if all_bets:
            st.subheader("📈 Recent Crash History")
            crash_multipliers = [row[4] for row in all_bets][::-1]
            fig = go.Figure(data=go.Scatter(y=crash_multipliers, mode='lines+markers'))
            fig.update_layout(
                xaxis_title="Game Number",
                yaxis_title="Crash Multiplier (x)",
                title="Crash Multiplier over Last 50 Games",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

            # Display crash stats
            avg_multiplier = sum(crash_multipliers) / len(crash_multipliers)
            max_multiplier = max(crash_multipliers)
            min_multiplier = min(crash_multipliers)
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Average Multiplier", f"{avg_multiplier:.2f}x")
            col2.metric("Highest Multiplier", f"{max_multiplier:.2f}x")
            col3.metric("Lowest Multiplier", f"{min_multiplier:.2f}x")
        else:
            st.info("No game history available yet")
    
    # ----------------- Leaderboard Tab -----------------
    with tabs[3]:
        users = get_all_users()
        if users:
            st.subheader("🏆 Global Leaderboard")
            
            # Prepare data for leaderboard, filtering out admin users
            leaderboard_data = []
            for user in users:
                if not user[4]:  # Check if the user is not an admin
                    total_bets = get_total_bets(user[1])  # Get total number of bets for the user
                    leaderboard_data.append({
                        "Username": user[1],
                        "Total Bets": total_bets,  # This now represents the count of bets
                        "Balance": user[2],
                    })
            
            # Assign ranks starting from 1
            for rank, user in enumerate(leaderboard_data, start=1):
                user["Rank"] = rank
            
            # Create DataFrame with the desired column order
            leaderboard_df = pd.DataFrame(leaderboard_data)[["Rank", "Username", "Total Bets", "Balance"]]
            
            # Display leaderboard with conditional formatting
            st.dataframe(
                leaderboard_df,
                column_config={
                    "Rank": st.column_config.NumberColumn("Rank"),
                    "Balance": st.column_config.NumberColumn(format="₹%.2f"),
                },
                use_container_width=True,
                hide_index=True
            )
            
            # Show user's position if not in top 10
            user_rank = next((i + 1 for i, user in enumerate(leaderboard_data) if user["Username"] == st.session_state.username), None)
            
            # Check if user_rank is None before comparison
            if user_rank is not None:
                if user_rank > 10:
                    user_data = next(user for user in leaderboard_data if user["Username"] == st.session_state.username)
                    st.subheader(f"Your Position: #{user_rank}")
                    st.write(f"Balance: ₹{user_data['Balance']:.2f}")
                    st.write(f"Total Bets: {user_data['Total Bets']}")  # Display the count of bets
            else:
                st.info("You are not in the leaderboard.")
        else:
            st.info("No players yet")

else:
    st.markdown("""
        <div style='text-align:center; margin-top:100px;'>
            <h1>🚀 Welcome to Crash Game!</h1>
            <p>Please login or register from the sidebar to start playing</p>
        </div>
    """, unsafe_allow_html=True)
