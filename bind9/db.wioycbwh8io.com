$TTL    604800
@       IN      SOA     ns1.wioycbwh8io.com. admin.wioycbwh8io.com. (
                        2024010101      ; Serial
                        604800          ; Refresh
                        86400           ; Retry
                        2419200         ; Expire
                        604800 )        ; Minimum TTL

; Name servers
@       IN      NS      ns1.wioycbwh8io.com.
@       IN      NS      ns2.wioycbwh8io.com.

; A records for name servers
ns1     IN      A       192.168.1.100
ns2     IN      A       192.168.1.100

; Main domain A record
@       IN      A       192.168.1.100

; WWW subdomain
www     IN      A       192.168.1.100

; Mail server (optional)
mail    IN      A       192.168.1.100
