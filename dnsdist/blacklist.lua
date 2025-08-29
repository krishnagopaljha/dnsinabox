driver = require "luasql.postgres"
env = assert(driver.postgres())

hostname = os.getenv("POSTGRES_HOST")
database = os.getenv("POSTGRES_DB")
username = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
resolve_blacklist_v4 = os.getenv("RESOLVE_BLACKLIST_IPv4") or "93.184.215.14"
resolve_blacklist_v6 = os.getenv("RESOLVE_BLACKLIST_IPv6") or "2606:2800:220:1:248:1893:25c8:1946"

-- Connect to PostgreSQL
con = assert(env:connect(database, username, password, hostname))

-- Declare a counter for custom metric
declareMetric('blacklist-db-hit', 'counter', 'Counts Blacklisted domain queries from dnsdist')

function dns_blacklist_check(dq)
    
    local domain = dq.qname:toString()
    local escaped_domain = con:escape(domain)
    
    -- Check blacklist
    local cursor = assert(con:execute(
        string.format("SELECT 1 FROM blacklist WHERE malicious = '%s' AND blocked = 1", escaped_domain)
    ))
    
    local result = cursor:fetch()
    cursor:close()
    
    if result then
        incMetric('blacklist-db-hit')
        return true
    end
    
    return false
end

-- Apply blacklist check + spoofing
addAction(
    LuaRule(dns_blacklist_check),
    SpoofAction({resolve_blacklist_v4, resolve_blacklist_v6}, {ttl = 1500})
)