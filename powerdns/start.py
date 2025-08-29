#!/usr/bin/env -S python3 -u
import os
import sys
import jinja2

program = sys.argv[0].split('-')[0]
product = os.path.basename(program)
apikey = os.getenv('PDNS_API_KEY')
lua_script = os.getenv('PDNS_LUA_SCRIPT')

# args = ['--lua-dns-script=/home/blacklist.lua', '--webserver=yes', ' --webserver-port', '8082', " --webserver-address", "0.0.0.0"]
args = [ 
    '--webserver=yes', '--webserver-port=8082', 
    # "--webserver-loglevel=detailed", 
    "--webserver-address=0.0.0.0", 
    # "--webserver-allow-from=127.0.0.1/0",
    "--webserver-allow-from=0.0.0.0/0",
    "--allow-from=0.0.0.0/0",
    # "--disable-packetcache=yes"
    "--dnssec=log-fail",
    "--max-cache-ttl=15",
    "--max-cache-bogus-ttl=15",
    "--max-cache-ttl=15",
    "--lua-dns-script=/home/blacklist.lua",
]

#if lua_script is not None:
 #   args.append(f"--lua-dns-script={lua_script}")

if apikey is not None:
    # $ curl -v -u=#:apikey -H 'X-API-Key:apikey' -H 'Host:powerdns' -H 'Content-type: application/json' http://3.109.5.238:8082/metrics
    args.append(f"--webserver-password={apikey}")

print("STARTING : ", [program]+args+sys.argv[1:])
os.execv(program, [program]+args+sys.argv[1:])