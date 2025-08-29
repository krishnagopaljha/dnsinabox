from fastapi import FastAPI
from contextlib import asynccontextmanager
from .database import db_manager, SQLModel, Blacklist
from .auth import auth_middleware, init_admin_password
from .api import router as api_router
from .ui import setup_ui 
from sqlmodel import Session, SQLModel, select
# --- FastAPI App Setup ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_admin_password()

    # Check if we have any databases configured
    if not db_manager.databases:
        raise RuntimeError("No databases configured")
    
    # Create database tables in all configured databases
    for db_key, db_config in db_manager.databases.items():
        try:
            engine = db_manager.get_engine(db_key)
            SQLModel.metadata.create_all(engine)
            # Add dummy data
            with Session(engine) as session:
                    dummy_data = [ 
                        Blacklist(original="facebook.com.", malicious="facedook.com."),
                        Blacklist(original="facebook.com.", malicious="facebo0k.com."),
                        Blacklist(original="bankok.com.", malicious="dankok.com."),
                        Blacklist(original="microsoft.com.", malicious="rnicrosoft.com."),
                        Blacklist(original="google.com.", malicious="goog1e.com."),
                    ]
                    for bl in dummy_data:
                        if not session.exec(select(Blacklist).where(Blacklist.malicious == bl.malicious)).first():
                            session.add(bl)
                    
                    session.commit()
        except Exception as e:
            raise
    yield

app = FastAPI(lifespan=lifespan)
app.middleware("http")(auth_middleware)
app.include_router(api_router)
setup_ui(app)