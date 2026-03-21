# ============ MAIN APPLICATION ============
def main():
    """Main dashboard application"""
    initialize_session_state()
    
    if not st.session_state.mt5_connected:
        # Show login page
        render_login_page()
    else:
        # Show main dashboard with sidebar
        render_sidebar_logged_in()
        render_main_dashboard()


if __name__ == "__main__":
    main()
