from .config import KEYWORDS, TLDS, SIMILAR_CHARS
from .database import Blacklist, get_session, ValidDomain, db_manager
from sqlmodel import select, Session
from jellyfish import jaro_winkler_similarity
import dns.resolver
def strip_tld(url):
    tld_list = ["com", "ru", "org", "in", "net", "uk", "info", "co", "au", "ai", "tk", "nl", "de", "cn"]
    
    def all_following_component_are_tld(components):
        for component in components:
            if component not in tld_list:
                return False
        return True

    components = url.split('.')
    domain = ""
    tld = []
    for idx, component in enumerate(components):
        if component in tld_list and all_following_component_are_tld(components[idx:]):
            domain = components[idx - 1]
            tld = components[idx:]
            break
    if tld:
        return domain, ".".join(tld)
    return None, None

def generate_typos(domain, tlds=None):
    if tlds is None:
        tlds = TLDS
    typos = set()
    for tld in tlds:
        for i in range(len(domain) + 1):
            for c in 'abcdefghijklmnopqrstuvwxyz0123456789.-_':
                typo = domain[:i] + c + domain[i:] + '.' + tld
                typos.add(typo)
        for i in range(len(domain)):
            typo = domain[:i] + domain[i+1:] + '.' + tld
            typos.add(typo)
        for i in range(len(domain)):
            for c in 'abcdefghijklmnopqrstuvwxyz0123456789.-_':
                if c != domain[i]:
                    typo = domain[:i] + c + domain[i+1:] + '.' + tld
                    typos.add(typo)
        for i in range(len(domain) - 1):
            typo = domain[:i] + domain[i+1] + domain[i] + domain[i+2:] + '.' + tld
            typos.add(typo)
    return typos

def generate_jaro_winkler(domain, tlds=None):
    if tlds is None:
        tlds = TLDS

    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    typos = []
    for tld in tlds:
        for i in range(len(domain)):
            for char in alphabet:
                typo = domain[:i] + char + domain[i+1:] + '.' + tld
                if typo != domain and jaro_winkler_similarity(domain, typo) > 0.8:
                    typos.append(typo)

                typo = domain[:i] + domain[i+1:] + '.' + tld
                if typo != domain and jaro_winkler_similarity(domain, typo) > 0.8:
                    typos.append(typo)

                if i < len(domain) - 1:
                    typo = domain[:i] + domain[i+1] + domain[i] + domain[i+2:] + '.' + tld
                    if typo != domain and jaro_winkler_similarity(domain, typo) > 0.8:
                        typos.append(typo)

                typo = domain[:i] + char + domain[i:] + '.' + tld
                if typo != domain and jaro_winkler_similarity(domain, typo) > 0.8:
                    typos.append(typo)

    return list(set(typos))

def generate_homographs(domain, tlds=None):
    if tlds is None:
        tlds = TLDS

    homograph_domains = set()
    for char in domain:
        if char.lower() in SIMILAR_CHARS:
            homographs = SIMILAR_CHARS[char.lower()]
            for homograph in homographs:
                for tld in tlds:
                    homograph_domains.add(domain.replace(char, homograph) + '.' + tld)
    return homograph_domains

def generate_ribbon_domains(domain, keywords=None, tlds=None):
    if keywords is None:
        keywords = KEYWORDS

    if tlds is None:
        tlds = TLDS

    ribbon_domains = set()
    for keyword in keywords:
        for tld in tlds:
            ribbon_domain = f"{domain}-{keyword}.{tld}"
            ribbon_domains.add(ribbon_domain)
    return ribbon_domains

# --- DNS Functions ---
def check_domain_existence(domain: str) -> bool:
    resolver = dns.resolver.Resolver()
    resolver.nameservers = ['8.8.8.8']
    try:
        resolver.resolve(domain, 'A', lifetime=5.0)
        return True
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, 
            dns.resolver.NoNameservers, dns.exception.Timeout):
        return False
    except Exception as e:
        return False

def check_domain_with_quad9(domain: str) -> bool:
    QUAD9_DNS_SERVER = '9.9.9.9'
    try:
        resolver = dns.resolver.Resolver(configure=False)
        resolver.nameservers = [QUAD9_DNS_SERVER]
        answers = resolver.resolve(domain)
        return bool(answers)
    except Exception as e:
        return False

# --- Worker Function ---
def worker(session: Session, valid_domain: ValidDomain, commit_every=50):
    engine = db_manager.get_engine()
    with Session(engine) as session:
        _domain, _tld = strip_tld(valid_domain.domain)
        if not _domain:
            print(f"Couldn't extract domain from: {valid_domain.domain}")
            return
            
        print("="*10)
        print(_domain)
        print("="*10)
        typos = generate_typos(_domain)
        homographs = generate_homographs(_domain)
        ribbon_domains = generate_ribbon_domains(_domain)
        jaro_winkler = generate_jaro_winkler(_domain)

        all_lookalike_domains = [*typos, *homographs, *ribbon_domains, *jaro_winkler]

        domain_idx = 0

        existing_blacklists = session.exec(select(Blacklist).where(Blacklist.original == f"{valid_domain.domain}.")).all()
        existing_malicious_variants = [bl.malicious[:-1] for bl in existing_blacklists] if existing_blacklists else []

        print("="*10)
        print(existing_blacklists)
        print("="*10)

        for domain in all_lookalike_domains:
            if domain not in existing_malicious_variants:
                if check_domain_existence(domain):
                    if check_domain_with_quad9(domain):
                        session.add(
                            Blacklist(original=f"{valid_domain.domain}.", malicious=f"{domain}.")
                        )

                        if domain_idx % commit_every == 0:
                            session.commit()

                        domain_idx += 1

        session.commit()
