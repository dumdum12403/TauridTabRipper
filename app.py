import streamlit as st
import sqlite3
import hashlib
import datetime
import pandas as pd

class UserManager:
    """Handle user authentication and usage tracking"""
    
    def __init__(self, db_path="users.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize user database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                tier TEXT DEFAULT 'free',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        
        # Usage tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                generation_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                month_year TEXT,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        """Hash password for storage"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def create_user(self, email, password):
        """Create new user account"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            password_hash = self.hash_password(password)
            cursor.execute(
                "INSERT INTO users (email, password_hash) VALUES (?, ?)",
                (email, password_hash)
            )
            
            conn.commit()
            conn.close()
            return True, "Account created successfully!"
        except sqlite3.IntegrityError:
            return False, "Email already exists!"
        except Exception as e:
            return False, f"Error creating account: {str(e)}"
    
    def authenticate_user(self, email, password):
        """Authenticate user login"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self.hash_password(password)
        cursor.execute(
            "SELECT id, tier FROM users WHERE email = ? AND password_hash = ?",
            (email, password_hash)
        )
        
        result = cursor.fetchone()
        
        if result:
            # Update last login
            cursor.execute(
                "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                (result[0],)
            )
            conn.commit()
            conn.close()
            return True, {"user_id": result[0], "email": email, "tier": result[1]}
        
        conn.close()
        return False, "Invalid email or password"
    
    def get_usage_count(self, user_id, month_year=None):
        """Get user's generation count for current month"""
        if not month_year:
            month_year = datetime.datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT COUNT(*) FROM usage WHERE user_id = ? AND month_year = ?",
            (user_id, month_year)
        )
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def log_usage(self, user_id, generation_type):
        """Log a generation usage"""
        month_year = datetime.datetime.now().strftime("%Y-%m")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO usage (user_id, generation_type, month_year) VALUES (?, ?, ?)",
            (user_id, generation_type, month_year)
        )
        
        conn.commit()
        conn.close()
    
    def can_generate(self, user_id, tier):
        """Check if user can generate based on their tier"""
        current_usage = self.get_usage_count(user_id)
        
        limits = {
            "free": 100,
            "tier1": 500,
            "unlimited": float('inf')
        }
        
        return current_usage < limits.get(tier, 0)

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
        st.session_state.user_info = None
    if 'user_manager' not in st.session_state:
        st.session_state.user_manager = UserManager()

def show_pricing_tiers():
    """Display pricing tiers"""
    st.markdown("## 🎵 Choose Your Plan")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🆓 Free Tier
        - **100 generations/month**
        - Basic tab generation
        - Text file export
        - Community support
        
        **$0/month**
        """)
        
    with col2:
        st.markdown("""
        ### 🎸 Tier 1 - Musician
        - **500 generations/month**
        - All Free features
        - Advanced features
        - PDF export
        - Priority support
        
        **$9.99/month**
        """)
        if st.button("Upgrade to Tier 1", key="tier1"):
            st.info("🚧 Payment integration coming soon!")
            
    with col3:
        st.markdown("""
        ### 🎤 Unlimited - Pro
        - **Unlimited generations**
        - All Tier 1 features
        - Batch processing
        - API access
        - Premium support
        
        **$29.99/month**
        """)
        if st.button("Upgrade to Unlimited", key="unlimited"):
            st.info("🚧 Payment integration coming soon!")

def show_login_page():
    """Display login/signup page"""
    st.title("🎸 TabGenius - AI Guitar Tablature Generator")
    st.markdown("### Transform your music into guitar tabs with AI")
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.header("Login")
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login"):
            if email and password:
                success, result = st.session_state.user_manager.authenticate_user(email, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_info = result
                    st.rerun()
                else:
                    st.error(result)
            else:
                st.error("Please enter both email and password")
    
    with tab2:
        st.header("Create Account")
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        
        if st.button("Sign Up"):
            if new_email and new_password and confirm_password:
                if new_password == confirm_password:
                    success, message = st.session_state.user_manager.create_user(new_email, new_password)
                    if success:
                        st.success(message)
                        st.info("Please login with your new account")
                    else:
                        st.error(message)
                else:
                    st.error("Passwords don't match")
            else:
                st.error("Please fill in all fields")

def generate_demo_tab(prompt_type="text"):
    """Generate demo tablature"""
    demo_tabs = {
        "blues": """E|---0---3---0---3---0---|
B|---0---0---1---0---0---|
G|---0---0---0---0---0---|
D|---2---0---2---0---2---|
A|---2---2---3---2---2---|
E|---0---3---x---3---0---|""",
        
        "rock": """E|---3---2---0---2---3---|
B|---3---3---1---3---3---|
G|---0---2---0---2---0---|
D|---0---0---2---0---0---|
A|---2---x---3---x---2---|
E|---3---x---x---x---3---|""",
        
        "country": """E|---0---2---3---2---0---|
B|---1---3---3---3---1---|
G|---0---2---0---2---0---|
D|---2---0---0---0---2---|
A|---3---x---2---x---3---|
E|---x---x---3---x---x---|"""
    }
    
    if "blues" in prompt_type.lower():
        return demo_tabs["blues"]
    elif "rock" in prompt_type.lower():
        return demo_tabs["rock"]
    else:
        return demo_tabs["country"]

def show_main_app():
    """Display main application interface"""
    user_info = st.session_state.user_info
    user_manager = st.session_state.user_manager
    
    # Header with user info
    st.title("🎸 TabGenius")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.write(f"Welcome, {user_info['email']}")
    with col2:
        tier_display = {
            'free': '🆓 Free',
            'tier1': '🎸 Musician',
            'unlimited': '🎤 Pro'
        }
        st.write(f"Plan: {tier_display.get(user_info['tier'], 'Unknown')}")
    with col3:
        if st.button("Logout"):
            st.session_state.authenticated = False
            st.session_state.user_info = None
            st.rerun()
    
    # Usage tracking
    current_usage = user_manager.get_usage_count(user_info['user_id'])
    limits = {'free': 100, 'tier1': 500, 'unlimited': '∞'}
    limit = limits.get(user_info['tier'], 0)
    
    if user_info['tier'] != 'unlimited':
        progress = current_usage / limit if limit > 0 else 0
        st.progress(progress)
        st.write(f"Generations this month: {current_usage}/{limit}")
        
        if current_usage >= limit:
            st.error("You've reached your monthly limit! Upgrade your plan to continue.")
            show_pricing_tiers()
            return
    else:
        st.write(f"Generations this month: {current_usage} (Unlimited)")
    
    # Main functionality tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Text to Tab", "🎓 Music Lessons", "Demo Audio", "Upgrade Plan", "Billing"])
    
    with tab1:
        st.header("📝 Text to Tablature")
        st.write("Describe the music you want and AI will generate tablature")
        
        prompt = st.text_area(
            "Describe your music",
            placeholder="e.g., 'Dark blues in E minor with slow tempo'",
            help="Describe style, key, tempo, mood, etc."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            complexity = st.selectbox("Style", ["Blues", "Rock", "Country", "Folk"])
        with col2:
            difficulty = st.selectbox("Difficulty", ["Beginner", "Intermediate", "Advanced"])
        
        if st.button("Generate Tablature", key="text_gen"):
            if prompt and user_manager.can_generate(user_info['user_id'], user_info['tier']):
                with st.spinner("Generating tablature..."):
                    # Generate demo tab based on style
                    tab_result = generate_demo_tab(complexity)
                    
                    st.success("Tablature generated successfully!")
                    st.code(tab_result, language="text")
                    
                    # Log usage
                    user_manager.log_usage(user_info['user_id'], "text_to_tab")
                    
                    # Download button
                    tab_content = f"""Guitar Tablature - {complexity} Style
Generated from: {prompt}

{tab_result}

Generated by TabGenius"""
                    
                    st.download_button(
                        "Download Tab",
                        tab_content,
                        file_name=f"{complexity.lower()}_tab.txt",
                        mime="text/plain"
                    )
            elif not prompt:
                st.error("Please enter a description")
            else:
                st.error("Generation limit reached! Please upgrade your plan.")
    
    with tab2:# Music Lessons tab (this is your new tab)
    show_education_platform()
        
            
            
            
        
        
        
            
    
    with tab3:
        show_pricing_tiers()

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="TabGenius - AI Guitar Tablature Generator",
        page_icon="🎸",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main > .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stButton > button {
        background-color: #FF6B6B;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #FF5252;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)
    
    init_session_state()
    
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()
