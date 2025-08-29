import configparser
from pathlib import Path
from typing import Dict, Generator, Optional
from sqlmodel import create_engine, Session, SQLModel, Field, select
from .config import PASSWORD_FILE
import threading
# --- Models ---
class Blacklist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    blocked: int = Field(default=1)
    original: str
    malicious: str

    __tablename__ = "blacklist"

class ValidDomain(SQLModel):
    domain: str

class BlacklistUpdate(SQLModel):
    blocked: int

class DatabaseManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path='app/databases.ini'):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.config_path = config_path
                cls._instance.databases: Dict[str, dict] = {}
                cls._instance.current_db = ""
                cls._instance._engine_lock = threading.RLock()
                cls._instance.load_config()
        return cls._instance
        
    def load_config(self):
        config = configparser.ConfigParser()
        config.read(Path(self.config_path))
        
        for section in config.sections():
            if section.startswith('database.'):
                key = section.split('.')[1]
                self.databases[key] = {
                    'name': config.get(section, 'name'),
                    'host': config.get(section, 'host'),
                    'port': config.get(section, 'port'),
                    'user': config.get(section, 'user'),
                    'password': config.get(section, 'password'),
                    'db': config.get(section, 'db', fallback='blacklist_db')
                }
                if not self.current_db:
                    self.current_db = key
    
    def get_engine(self, db_key: Optional[str] = None):
        with self._engine_lock:
            key = db_key or self.current_db
            if key not in self.databases:
                raise ValueError(f"Database key '{key}' not found")
            
            db_config = self.databases[key]
            conn_url = (
                f"postgresql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['db']}"
            )
            return create_engine(conn_url, echo=True)
    
    def get_session(self, db_key: Optional[str] = None) -> Generator[Session, None, None]:
        engine = self.get_engine(db_key)
        with Session(engine) as session:
            yield session
    
    def get_database_options(self):
        return {key: config['name'] for key, config in self.databases.items()}
    
    def set_current_db(self, db_key: str):
        with self._engine_lock:
            if db_key in self.databases:
                self.current_db = db_key
            else:
                raise ValueError(f"Invalid database key: {db_key}")

# Initialize the database manager
db_manager = DatabaseManager()

# For FastAPI dependency compatibility
def get_session() -> Generator[Session, None, None]:
    yield from db_manager.get_session()