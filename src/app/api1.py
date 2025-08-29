from typing import List
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from .database import get_session, Blacklist, ValidDomain, BlacklistUpdate, db_manager
from sqlmodel import Session, select, or_

# --- Helper Function for String Conversion ---
def represent_string_with_utf8_bytes(input_string: str) -> str:
    """
    Converts a string so that any multi-byte characters are represented
    by their UTF-8 byte sequence, while standard ASCII characters remain as they are.
    For example: 'adoḅe.com' becomes 'ado\\225\\184\\133e.com'.
    """
    if not isinstance(input_string, str):
        return input_string
        
    result_parts = []
    for char in input_string:
        # Encode the character into bytes using UTF-8
        encoded_char_bytes = char.encode('utf-8')

        # Check if the character is a standard single-byte character (ASCII)
        if len(encoded_char_bytes) == 1:
            # If it is, keep the character as is
            result_parts.append(char)
        else:
            # If it's a multi-byte character, convert it to its byte representation
            formatted_bytes = "".join([f"\\{byte}" for byte in encoded_char_bytes])
            result_parts.append(formatted_bytes)

    # Join all the parts together to form the final string
    return "".join(result_parts)

router = APIRouter()

# --- API Endpoints ---
@router.get("/blacklist", response_model=List[Blacklist])
def get_all_blacklist(session: Session = Depends(get_session),
                      offset: int = 0,
                      limit: int = Query(default=100, ge=1, le=100),
                      original: str = None,
                      malicious: str = None):
    query = select(Blacklist)

    if original:
        query = query.where(Blacklist.original == original)
    if malicious:
        # Convert search query to match the stored format
        encoded_malicious = represent_string_with_utf8_bytes(malicious)
        
        # Add trailing dot to match the stored format if it's not there
        if not encoded_malicious.endswith('.'):
            encoded_malicious += '.'
            
        query = query.where(Blacklist.malicious == encoded_malicious)

    blacklist_domains = session.exec(query.offset(offset).limit(limit)).all()
    return blacklist_domains

@router.post("/blacklist", response_model=Blacklist)
def create_blacklist(*, session: Session = Depends(get_session), blacklist: Blacklist):
    # 1. Set default for original domain if not provided
    if not blacklist.original:
        blacklist.original = "Manually Entered"

    # 2. Convert the malicious domain and ensure it has a trailing dot
    if blacklist.malicious:
        converted_malicious = represent_string_with_utf8_bytes(blacklist.malicious)
        
        # Add a trailing dot if it's missing
        if not converted_malicious.endswith('.'):
            converted_malicious += '.'
            
        blacklist.malicious = converted_malicious
        
    db_blacklist = Blacklist.model_validate(blacklist)
    session.add(db_blacklist)
    session.commit()
    session.refresh(db_blacklist)
    return db_blacklist

@router.get("/blacklist/stats")
def get_stats_blacklist(session: Session = Depends(get_session)):
    all_original_domains = session.exec(select(Blacklist.original).distinct()).all()
    
    stats = {}
    for original in all_original_domains:
        count = session.exec(select(Blacklist).where(Blacklist.original == original)).all()
        stats[original] = len(count)

    return stats

@router.post("/blacklist/add-to-queue")
def blacklist_queue(*, session: Session = Depends(get_session), valid_domain: ValidDomain, background_tasks: BackgroundTasks):
    background_tasks.add_task(worker, valid_domain, db_key=db_manager.current_db)
    return {"status": "success", "domain": valid_domain.domain}

@router.patch("/blacklist/{entry_id}", response_model=Blacklist)
def update_blacklist(
    *,
    session: Session = Depends(get_session),
    entry_id: int,
    update_data: BlacklistUpdate
):
    db_entry = session.get(Blacklist, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    db_entry.blocked = update_data.blocked
    session.add(db_entry)
    session.commit()
    session.refresh(db_entry)
    return db_entry

@router.delete("/blacklist/{entry_id}")
def delete_blacklist(
    *,
    session: Session = Depends(get_session),
    entry_id: int
):
    db_entry = session.get(Blacklist, entry_id)
    if not db_entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    session.delete(db_entry)
    session.commit()
    return {"status": "success"}