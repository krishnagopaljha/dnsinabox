from typing import List 
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, Query
from .database import get_session, Blacklist, ValidDomain, BlacklistUpdate, db_manager, get_session
from .lookalike import worker
from sqlmodel import Session, select

router = APIRouter()

# Domain normalization helper
def normalize_domain(domain: str) -> str:
    if not domain:
        return "."
    domain = domain.strip().rstrip('.')  # Clean whitespace and existing dots
    if not domain:
        return "."
    try:
        # Convert to ASCII/Punycode format
        ascii_domain = domain.encode('idna').decode('ascii')
    except Exception as e:
        raise ValueError(f"Invalid domain format: {domain} ({str(e)})")
    return ascii_domain + '.'  # Append trailing dot

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
        query = query.where(Blacklist.malicious == malicious)

    blacklist_domains = session.exec(query.offset(offset).limit(limit)).all()
    return blacklist_domains

@router.post("/blacklist", response_model=Blacklist)
def create_blacklist(*, session: Session = Depends(get_session), blacklist: Blacklist):
    try:
        # Normalize domains before saving
        normalized_original = normalize_domain(blacklist.original)
        normalized_malicious = normalize_domain(blacklist.malicious)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Create validated object with normalized domains
    db_blacklist = Blacklist(
        original=normalized_original,
        malicious=normalized_malicious,
        blocked=blacklist.blocked
    )
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
    try:
        # Normalize domain before queuing
        valid_domain.domain = normalize_domain(valid_domain.domain)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
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