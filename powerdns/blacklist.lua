driver = require "luasql.postgres"
env = assert( driver.postgres() )

hostname = os.getenv("POSTGRES_HOST") -- "postgres"
database = os.getenv("POSTGRES_DB") -- "powerdns"
username = os.getenv("POSTGRES_USER") -- "root"
password = os.getenv("POSTGRES_PASSWORD") -- "secret"

resolve_blacklist = os.getenv("RESOLVE_BLACKLIST") -- "93.184.215.14"

con = assert(env:connect(database, username, password, hostname))

blacklist_db_hit = getMetric("blacklist_db_hit")

function preresolve ( dq )
        -- -- if no error, print success else print failure
        -- if pcall(resolve_func, dq) then
        --         print("Success")
        -- else
        --         con:close()
        --         con = assert(env:connect(database, username, password, hostname))
        -- end
        return resolve_func(dq)
end

function resolve_func( dq )
        pdnslog("Got question for "..dq.qname:toString().." from "..dq.remoteaddr:toString().." to "..dq.localaddr:toString())

        domain = dq.qname:toString()
        -- pdnslog(domain, pdns.loglevels.Info)
        local sth = assert (con:execute( string.format("SELECT 1 FROM blacklist WHERE malicious = '%s'", con:escape( domain )) ) )
        if sth:fetch() then 
                blacklist_db_hit:inc()
                pdnslog("- Dopping query as the domain may be considered a phishing attempt.")
                -- dq.appliedPolicy.policyKind = pdns.policykinds.Drop
                dq:addAnswer(pdns.A, resolve_blacklist)
                return true
        end
        pdnslog("- Accepting query")
        return false
end