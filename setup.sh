chmod +x ./powerdns/start.py
sudo mkdir ./dnscollector/.var
sudo chmod 777 ./dnscollector/.var
sudo mkdir /tmp/prometheus
sudo chmod 777 /tmp/prometheus
sudo sysctl -w net.core.rmem_max=4194304
sudo sysctl -w net.core.wmem_max=4194304
