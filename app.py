import streamlit as st
import sqlite3
import hashlib
import datetime
from io import BytesIO
import pandas as pd

# Import your tabulature engine (assuming it's in a separate file)
# from tabulature_engine import TabulatureEngine

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
                last_login TIMESTAMP,
                stripe_customer_id TEXT
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
    # Uncomment when you have the TabulatureEngine ready
    # if 'tab_engine' not in st.session_state:
    #     st.session_state.tab_engine = TabulatureEngine()

def show_pricing_tiers():
    """Display pricing tiers"""
    st.markdown("## 🎵 Choose Your Plan")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🆓 Free Tier
        - **100 generations/month**
        - Audio-to-tab transcription
        - Basic MIDI generation
        - Text file export
        
        **$0/month**
        """)
        
    with col2:
        st.markdown("""
        ### 🎸 Tier 1 - Musician
        - **500 generations/month**
        - All Free features
        - Advanced chord detection
        - PDF export
        - Priority processing
        
        **$9.99/month**
        """)
        if st.button("Upgrade to Tier 1", key="tier1"):
            st.info("Stripe integration would go here")
            
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
            st.info("Stripe integration would go here")

def show_login_page():
    """Display login/signup page"""
    st.title("🎸 TabGenius - AI Guitar Tablature Generator")
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["Audio to Tab", "Text to Tab", "MIDI to Tab", "Upgrade Plan"])
    
    with tab1:
        st.header("🎵 Audio to Tablature")
        st.write("Upload an audio file to generate guitar tablature")
        
        uploaded_file = st.file_uploader(
            "Choose audio file", 
            type=['mp3', 'wav', 'm4a', 'flac'],
            help="Supported formats: MP3, WAV, M4A, FLAC"
        )
        
        if uploaded_file is not None:
            if st.button("Generate Tablature", key="audio_gen"):
                if user_manager.can_generate(user_info['user_id'], user_info['tier']):
                    with st.spinner("Processing audio..."):
                        # Save uploaded file temporarily
                        temp_path = f"temp_{uploaded_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        
                        # Process with your tabulature engine
                        # tab_result = st.session_state.tab_engine.transcribe_audio_to_tab(temp_path)
                        tab_result = "E|---0---2---3---2---0---|\nB|---1---3---3---3---1---|\nG|---0---2---0---2---0---|\nD|---2---0---0---0---2---|\nA|---3---x---2---x---3---|\nE|---x---x---3---x---x---|"  # Demo
                        
                        st.code(tab_result, language="text")
                        
                        # Log usage
                        user_manager.log_usage(user_info['user_id'], "audio_to_tab")
                        
                        # Download button
                        st.download_button(
                            "Download Tab",
                            tab_result,
                            file_name=f"{uploaded_file.name}_tab.txt",
                            mime="text/plain"
                        )
                        
                        # Clean up temp file
                        import os
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    st.error("Generation limit reached! Please upgrade your plan.")
    
    with tab2:
        st.header("📝 Text to Tablature")
        st.write("Describe the music you want and AI will generate tablature")
        
        prompt = st.text_area(
            "Describe your music",
            placeholder="e.g., 'Dark blues in E minor with slow tempo'",
            help="Describe style, key, tempo, mood, etc."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            num_measures = st.slider("Number of measures", 1, 8, 4)
        with col2:
            complexity = st.selectbox("Complexity", ["Simple", "Intermediate", "Advanced"])
        
        if st.button("Generate from Text", key="text_gen"):
            if prompt and user_manager.can_generate(user_info['user_id'], user_info['tier']):
                with st.spinner("Generating tablature..."):
                    # Process with your tabulature engine
                    # music_info = st.session_state.tab_engine.interpret_prompt(prompt)
                    # midi_path = st.session_state.tab_engine.generate_midi(music_info, num_measures=num_measures)
                    # tab_result = st.session_state.tab_engine.midi_to_tab(midi_path)
                    
                    tab_result = "E|---0---2---3---2---0---|\nB|---1---3---3---3---1---|\nG|---0---2---0---2---0---|\nD|---2---0---0---0---2---|\nA|---3---x---2---x---3---|\nE|---x---x---3---x---x---|"  # Demo
                    
                    st.code(tab_result, language="text")
                    
                    # Log usage
                    user_manager.log_usage(user_info['user_id'], "text_to_tab")
                    
                    st.download_button(
                        "Download Tab",
                        tab_result,
                        file_name="generated_tab.txt",
                        mime="text/plain"
                    )
            elif not prompt:
                st.error("Please enter a description")
            else:
                st.error("Generation limit reached! Please upgrade your plan.")
    
    with tab3:
        st.header("🎹 MIDI to Tablature")
        st.write("Convert MIDI files to guitar tablature")
        
        midi_file = st.file_uploader(
            "Choose MIDI file",
            type=['mid', 'midi'],
            help="Upload a MIDI file to convert to guitar tab"
        )
        
        if midi_file is not None:
            if st.button("Convert MIDI", key="midi_gen"):
                if user_manager.can_generate(user_info['user_id'], user_info['tier']):
                    with st.spinner("Converting MIDI..."):
                        # Save and process MIDI file
                        temp_path = f"temp_{midi_file.name}"
                        with open(temp_path, "wb") as f:
                            f.write(midi_file.getbuffer())
                        
                        # Process with your tabulature engine
                        # tab_result = st.session_state.tab_engine.midi_to_tab(temp_path)
                        tab_result = "E|---0---2---3---2---0---|\nB|---1---3---3---3---1---|\nG|---0---2---0---2---0---|\nD|---2---0---0---0---2---|\nA|---3---x---2---x---3---|\nE|---x---x---3---x---x---|"  # Demo
                        
                        st.code(tab_result, language="text")
                        
                        # Log usage
                        user_manager.log_usage(user_info['user_id'], "midi_to_tab")
                        
                        st.download_button(
                            "Download Tab",
                            tab_result,
                            file_name=f"{midi_file.name}_tab.txt",
                            mime="text/plain"
                        )
                        
                        # Clean up
                        import os
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                else:
                    st.error("Generation limit reached! Please upgrade your plan.")
    
    with tab4:
        show_pricing_tiers()

def main():
    """Main application entry point"""
    st.set_page_config(
        page_title="TabGenius - AI Guitar Tablature Generator",
        page_icon="🎸",
        layout="wide"
    )
    
    init_session_state()
    
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()

if __name__ == "__main__":
    main()