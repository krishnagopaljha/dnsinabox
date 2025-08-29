from nicegui import ui
from fastapi import FastAPI, Request
from .api import get_all_blacklist, create_blacklist, get_stats_blacklist, update_blacklist, delete_blacklist, blacklist_queue
from .database import Blacklist, get_session, ValidDomain, BlacklistUpdate, DatabaseManager, db_manager
from .lookalike import worker
from .auth import is_authenticated, create_session, delete_session, init_admin_password, verify_password
from sqlmodel import Session, SQLModel, select
import threading

def setup_ui(app: FastAPI):
    # Custom CSS for modern styling
    ui.add_head_html('''
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
        <style>
            * {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            body { margin: 0; padding: 0; }
            .mono { font-family: 'JetBrains Mono', monospace; }
            .glass { backdrop-filter: blur(20px); background: rgba(255, 255, 255, 0.7); }
            .gradient-bg { 
                background: linear-gradient(135deg, #fff9e6 0%, #fff3cd 25%, #ffeaa7 50%, #fdcb6e 75%, #e17055 100%); 
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: flex-start;
                padding: 2rem 1rem;
            }
            .card-shadow { box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1), 0 4px 10px rgba(0, 0, 0, 0.05); }
            .hover-lift { transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }
            .hover-lift:hover { transform: translateY(-2px); box-shadow: 0 15px 35px rgba(0, 0, 0, 0.15); }
            .text-gradient { background: linear-gradient(135deg, #d35400, #e74c3c, #f39c12); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
            .btn-primary { background: linear-gradient(135deg, #e17055 0%, #d63031 100%); border: none; }
            .btn-secondary { background: linear-gradient(135deg, #fdcb6e 0%, #e17055 100%); border: none; }
            .btn-success { background: linear-gradient(135deg, #00b894 0%, #00a085 100%); border: none; }
            .status-card { border-left: 4px solid #e17055; }
            .page-container { 
                width: 100%; 
                max-width: 1200px; 
                margin: 0 auto; 
                padding: 2rem; 
            }
        </style>
    ''')

    # --- UI Components ---
    @ui.page('/login')
    async def login(request: Request):
        if is_authenticated(request):
            ui.navigate.to('/')
            return
        
        hashed_password = init_admin_password()
        
        def try_login():
            if verify_password(password.value, hashed_password):
                session_id = create_session("admin")
                ui.run_javascript(f'''
                    document.cookie = "session_id={session_id}; path=/; max-age=3600; secure=false; samesite=lax";
                    window.location.href = "/";
                ''')
            else:
                ui.notify("Invalid credentials", type='negative')
        
        # Main container with perfect centering
        with ui.element('div').classes('fixed inset-0 flex items-center justify-center p-4 gradient-bg'):
            # Card container with strict width constraints
            with ui.element('div').classes('w-full max-w-md'):
                with ui.card().classes('glass card-shadow hover-lift border-0 w-full'):
                    # Centered column for all content
                    with ui.column().classes('p-8 space-y-6 items-center w-full'):
                        # Icon and headings
                        ui.icon('security', size='3rem').classes('text-orange-600')
                        ui.label('Admin Portal').classes('text-3xl font-bold text-center text-gray-800 text-gradient')
                        ui.label('Secure access to domain management').classes('text-sm text-center text-gray-600 font-medium')
                        
                        # Form elements (full width but centered in parent)
                        with ui.column().classes('w-full space-y-4'):
                            password = ui.input('Password', password=True, password_toggle_button=True) \
                                .classes('w-full') \
                                .props('outlined dense bg-color="white" color="orange-7"')
                            password.on('keydown.enter', try_login)
                            
                            ui.button('Sign In', on_click=try_login) \
                                .classes('w-full py-3 text-white font-semibold btn-primary rounded-lg shadow-lg hover-lift')
                        
                        # Credentials card (full width)
                        with ui.card().classes('bg-orange-50 border border-orange-200 w-full mt-4'):
                            ui.label('🔑 Default credentials').classes('text-xs font-semibold text-orange-700 text-center')
                            ui.label('Password: admin_password').classes('text-xs text-orange-600 mono text-center')

    @ui.page('/logout')
    async def logout(request: Request):
        session_id = request.cookies.get("session_id")
        if session_id:
            delete_session(session_id)
        
        ui.run_javascript('''
            document.cookie = "session_id=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
            window.location.href = "/login";
        ''')
    db_manager = DatabaseManager()
    def database_switcher():
        options = db_manager.get_database_options()
        with ui.select(options, value=db_manager.current_db) as select:
            select.classes('w-64')
            
            def on_change():
                # Show loading overlay
                with ui.dialog() as loading_dialog:
                    loading_dialog.props('persistent')
                    with ui.card().classes('p-8 text-center'):
                        ui.spinner('dots', size='xl').classes('text-orange-500')
                        ui.label('Switching database...').classes('mt-4 text-lg font-medium')
                        ui.label('Please wait while we load the new database').classes('text-gray-500')
                
                loading_dialog.open()
                
                async def switch_database():
                    try:
                        await ui.run_javascript('new Promise(resolve => setTimeout(resolve, 100))')  # Small delay for UI update
                        db_manager.set_current_db(select.value)
                        blacklist_table.refresh()
                        loading_dialog.close()
                        ui.notify(f"Switched to database: {db_manager.databases[select.value]['name']}", type='positive')
                    except Exception as e:
                        loading_dialog.close()
                        ui.notify(f"Error switching database: {e}", type='negative')
                        # Revert selection on error
                        select.value = db_manager.current_db
                
                ui.timer(0.1, switch_database, once=True)
        
        select.on('update:model-value', on_change)

    @ui.refreshable
    def blacklist_table():  
        # Modern stats display
        try:
            engine = db_manager.get_engine()
            with Session(engine) as session:
                stats = get_stats_blacklist(session=session)
            
            with ui.row().classes('w-full gap-6 mb-8 justify-center'):
                for i, (domain, count) in enumerate(stats.items()):
                    with ui.card().classes('flex-1 min-w-[220px] max-w-[280px] glass card-shadow hover-lift border-0 status-card'):
                        with ui.column().classes('p-6 space-y-2'):
                            ui.label(domain).classes('text-sm font-semibold text-gray-700 uppercase tracking-wider')
                            ui.label(f"{count:,}").classes('text-4xl font-bold text-orange-600')
                            ui.label('domains blocked').classes('text-xs text-gray-500 font-medium')
                            
        except Exception as e:
            ui.notify(f"Error loading stats: {e}", type='negative')
        
        # Modern domain table
        try:
            engine = db_manager.get_engine()
            with Session(engine) as session:
                query = select(Blacklist).order_by(Blacklist.id)
                blacklist_entries = session.exec(query.limit(100)).all()
                
                # Table header with modern styling
                with ui.card().classes('w-full glass card-shadow border-0 overflow-hidden'):
                    with ui.column().classes('w-full'):
                        # Header
                        with ui.row().classes('w-full p-4 bg-gradient-to-r from-orange-500 to-red-500 text-white'):
                            ui.label('ID').classes('w-16 font-semibold text-xs uppercase tracking-wider')
                            ui.label('Original Domain').classes('flex-1 font-semibold text-xs uppercase tracking-wider')
                            ui.label('Malicious Domain').classes('flex-1 font-semibold text-xs uppercase tracking-wider') 
                            ui.label('Status').classes('w-24 text-center font-semibold text-xs uppercase tracking-wider')
                            ui.label('Actions').classes('w-24 text-center font-semibold text-xs uppercase tracking-wider')
                        
                        # Data rows with alternating background
                        for i, entry in enumerate(blacklist_entries):
                            bg_class = 'bg-white' if i % 2 == 0 else 'bg-orange-50'
                            with ui.row().classes(f'w-full p-4 border-b border-orange-100 {bg_class} items-center hover:bg-orange-100 transition-colors'):
                                ui.label(str(entry.id)).classes('w-16 text-gray-600 font-mono text-sm')
                                ui.label(entry.original).classes('flex-1 text-gray-800 font-medium text-sm')
                                ui.label(entry.malicious).classes('flex-1 text-gray-800 font-mono text-sm')
                                
                                # Modern toggle switch
                                with ui.element('div').classes('w-24 flex justify-center'):
                                    switch = ui.switch(value=bool(entry.blocked)).props('color="orange" size="sm"')
                                    switch.on('update:model-value', lambda e, entry_id=entry.id: toggle_blocked(entry_id, e.args[0] if e.args else False))
                                
                                # Modern delete button
                                with ui.element('div').classes('w-24 flex justify-center'):
                                    ui.button(icon='delete_outline', on_click=lambda entry_id=entry.id: delete_entry(entry_id)) \
                                        .props('flat dense color="red-7" size="sm"') \
                                        .classes('hover-lift')

        except Exception as e:
            ui.notify(f"Error loading data: {e}", type='negative')
            with ui.card().classes('w-full p-8 text-center glass'):
                ui.icon('error_outline', size='3rem').classes('text-red-400')
                ui.label("Failed to load blacklist data").classes('text-red-600 font-semibold')

    def show_add_dialog():
        with ui.dialog() as dialog:
            with ui.element('div').classes('w-full max-w-lg'):
                with ui.card().classes('glass card-shadow border-0 w-full'):
                    with ui.column().classes('p-8 space-y-6 items-center w-full'):
                        # Icon and headings
                        ui.icon('add_circle_outline', size='2.5rem').classes('text-orange-600')
                        ui.label("Add Malicious Domain").classes('text-2xl font-bold text-center text-gray-800')
                        ui.label("Register a new domain to be blocked").classes('text-sm text-center text-gray-600')
                            
                        # Form elements (full width but centered in parent)
                        with ui.column().classes('w-full space-y-4'):
                            original_input = ui.input('Original Domain (Optional)') \
                                .classes('w-full') \
                                .props('outlined dense bg-color="white" color="orange-7"')
                            malicious_input = ui.input('Malicious Domain *') \
                                .classes('w-full') \
                                .props('outlined dense bg-color="white" color="orange-7" required')
                                
                            with ui.row().classes('w-full justify-center gap-3'):
                                ui.button('Cancel', on_click=dialog.close) \
                                    .classes('px-6 py-2 bg-gray-200 text-gray-700 rounded-lg hover-lift')
                                ui.button('Add Domain', on_click=lambda: add_entry(
                                    original_input.value,
                                    malicious_input.value,
                                    dialog
                                )).classes('px-6 py-2 text-white font-semibold btn-primary rounded-lg hover-lift')
            
        dialog.open()

    def toggle_blocked(entry_id: int, state: bool):
        try:
            engine = db_manager.get_engine()
            with Session(engine) as session:
                update_blacklist(session=session, entry_id=entry_id, update_data=BlacklistUpdate(blocked=int(state)))
            ui.notify(f"Status updated for domain #{entry_id}", type='positive')
            blacklist_table.refresh()
        except Exception as e:
            ui.notify(f"Error updating status: {e}", type='negative')

    def delete_entry(entry_id: int):
        def handle_delete():
            try:
                engine = db_manager.get_engine()
                with Session(engine) as session:
                    delete_blacklist(session=session, entry_id=entry_id)
                ui.notify(f"Domain #{entry_id} deleted successfully", type='positive')
                blacklist_table.refresh()
                dialog.close()
            except Exception as e:
                ui.notify(f"Error deleting entry: {e}", type='negative')
        
        with ui.dialog() as dialog:
            with ui.card().classes('glass card-shadow border-0'):
                with ui.column().classes('p-6 space-y-4'):
                    ui.icon('warning', size='2rem').classes('mx-auto text-orange-600')
                    ui.label(f"Delete Domain #{entry_id}?").classes('text-lg font-semibold text-center')
                    ui.label("This action cannot be undone").classes('text-sm text-gray-600 text-center')
                    
                    with ui.row().classes('w-full justify-center gap-3'):
                        ui.button("Cancel", on_click=dialog.close) \
                            .classes('px-4 py-2 bg-gray-200 text-gray-700 rounded-lg')
                        ui.button("Delete", on_click=handle_delete) \
                            .classes('px-4 py-2 bg-red-500 text-white rounded-lg hover-lift')
        
        dialog.open()

    def add_entry(original: str, malicious: str, dialog: ui.dialog):
        if not malicious:
            ui.notify("Malicious domain is required", type='negative')
            return
        try:
            engine = db_manager.get_engine()
            with Session(engine) as session:
                create_blacklist(session=session, blacklist=Blacklist(
                    original=original or 'Manually Entered',
                    malicious=malicious,
                    blocked=1
                ))
            
            ui.notify("Domain added successfully!", type='positive')
            dialog.close()
            blacklist_table.refresh()
        except Exception as e:
            ui.notify(f"Error adding domain: {e}", type='negative')

    @ui.page('/')
    async def index(request: Request):
        with ui.element('div').classes('gradient-bg min-h-screen flex justify-center p-4'):
            with ui.column().classes("page-container space-y-8 items-center"):
                # Modern header
                with ui.row().classes('w-full items-center justify-between mb-8'):
                    with ui.row().classes('items-center gap-4'):
                            ui.icon('database').classes('text-blue-500')
                            database_switcher()
                    with ui.column():
                        ui.label("Domain Security Center").classes("text-4xl font-bold text-gradient")
                        ui.label("Advanced malicious domain detection & blacklisting").classes("text-lg text-gray-600 font-medium")
                    
                    ui.button("Sign Out", icon='logout', on_click=lambda: ui.navigate.to('/logout')) \
                        .classes('px-6 py-3 bg-red-500 text-white rounded-lg hover-lift font-semibold')
                
                # Action cards with modern grid
                with ui.grid(columns=2).classes("w-full gap-8 mb-8 justify-center"):
                    # Authentic Domain Analysis Card
                    with ui.card().classes("glass card-shadow hover-lift border-0 border-l-4 border-l-green-500"):
                        with ui.column().classes("p-8 space-y-6"):
                            with ui.row().classes('items-center space-x-3'):
                                ui.icon('verified', size='2rem').classes('text-green-600')
                                ui.label("Domain Analysis").classes("text-xl font-bold text-gray-800")
                            
                            ui.label("Enter an authentic domain to automatically discover and blacklist malicious lookalike domains using advanced detection algorithms.").classes("text-gray-600 leading-relaxed")
                            
                            original_input = ui.input(label="Authentic Domain", placeholder="example.com") \
                                .classes("w-full") \
                                .props('outlined dense bg-color="white" color="green-7"')
                            
                            async def submit_original():
                                domain = original_input.value
                                if not domain:
                                    ui.notify("Please enter a domain", type='warning')
                                    return
                                
                                with ui.card().classes('bg-blue-50 border border-blue-200 p-4'):
                                    with ui.row().classes('items-center space-x-2'):
                                        ui.spinner(size='sm', color='blue')
                                        ui.label("Analyzing domain... This may take several minutes").classes('text-blue-700 font-medium')
                    
                                def background_work():
                                    try:
                                        engine = db_manager.get_engine()
                                        with Session(engine) as session:
                                            worker(session, ValidDomain(domain=domain))
                                        ui.notify("Analysis complete! Results added to blacklist", type='positive')
                                    except Exception as e:
                                        ui.notify(f"Error processing domain: {e}", type='negative')
                                    finally:
                                        ui.timer(0.1, lambda: blacklist_table.refresh(), once=True)
                                
                                thread = threading.Thread(target=background_work, daemon=True)
                                thread.start()
                            
                            ui.button("Start Analysis", icon="analytics", on_click=submit_original) \
                                .classes("w-full py-3 text-white font-semibold btn-success rounded-lg hover-lift")

                    # Manual Entry Card
                    with ui.card().classes("glass card-shadow hover-lift border-0 border-l-4 border-l-red-500"):
                        with ui.column().classes("p-8 space-y-6"):
                            with ui.row().classes('items-center space-x-3'):
                                ui.icon('report', size='2rem').classes('text-red-600')
                                ui.label("Manual Entry").classes("text-xl font-bold text-gray-800")
                            
                            ui.label("Quickly add a known malicious domain to the blacklist for immediate blocking across your network.").classes("text-gray-600 leading-relaxed")
                            
                            malicious_input = ui.input(label="Malicious Domain", placeholder="malicious-site.com") \
                                .classes("w-full") \
                                .props('outlined dense bg-color="white" color="red-7"')
                            
                            async def submit_malicious():
                                domain = malicious_input.value
                                if not domain:
                                    ui.notify("Please enter a domain", type='warning')
                                    return
                                try:
                                    engine = db_manager.get_engine()
                                    with Session(engine) as session:
                                        create_blacklist(session=session, blacklist=Blacklist(
                                            original="Manual Entry",
                                            malicious=domain,
                                            blocked=1
                                        ))
                                    ui.notify("Domain blacklisted successfully!", type='positive')
                                    malicious_input.value = ""
                                    blacklist_table.refresh()
                                except Exception as e:
                                    ui.notify(f"Error adding domain: {e}", type='negative')
                            
                            ui.button("Add to Blacklist", icon="block", on_click=submit_malicious) \
                                .classes("w-full py-3 text-white font-semibold btn-primary rounded-lg hover-lift")
                
                # Blacklist Management Section
                with ui.card().classes("glass card-shadow border-0 w-full max-w-6xl"):
                    with ui.column().classes('p-8 space-y-6 items-center'):
                        with ui.row().classes('items-center justify-between w-full'):
                            with ui.column():
                                ui.label("Blacklist Management").classes("text-2xl font-bold text-gray-800")
                                ui.label("Monitor and manage your domain blacklist").classes("text-gray-600")
                            
                            ui.button("Add Domain", icon='add_circle', on_click=show_add_dialog) \
                                .classes('px-6 py-3 text-white font-semibold btn-secondary rounded-lg hover-lift')
                        
                        blacklist_table()

    # Configure NiceGUI with modern settings
    ui.run_with(
        app,
        mount_path='/',
        storage_secret='your_secure_secret_key_here',
        title="Domain Security Center",
        favicon="🛡️",
        dark=False,
        tailwind=True
    )