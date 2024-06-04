#!/bin/bash

#Aktualizace balíčkových repozitářů
sudo apt update

#instalace PWGEN
sudo apt install pwgen

#Instalace balíčku
sudo apt install -y apache2 mariadb-server mariadb-client python3 python3-pip

sudo apt-get install libmariadb-dev-compat

sudo pip install mysqlclient

PASS=`pwgen -1 -n 10`

${PASS}

sed -e "s/%PASS%/$PASS/g" < script_.php | sudo tee script.php 
sed -e "s/%PASS%/$PASS/g" < config_.cfg | sudo tee config.cfg 

#Přesun do složky s Python soubory
sudo mv API_server_3_10.py /var/www/html
sudo mv testing_api.py /var/www/html
sudo mv config.cfg /var/www/html
sudo mv requirements.txt /var/www/html
sudo mv script.php /var/www/html

#Instalace Python závislostí
sudo pip3 install -r /var/www/html/requirements.txt

#Vytvoření databáze
sudo mysql -u root -e "CREATE DATABASE IF NOT EXISTS Ecowitt_database;"

#Vytvoření uživatele s heslem
sudo mysql -u root -e "CREATE USER IF NOT EXISTS 'pi'@'localhost' IDENTIFIED BY '$PASS';" #místo root $PASS

#Přidání uživateli všechna oprávnění
sudo mysql -u root -e "GRANT ALL PRIVILEGES ON Ecowitt_database.* TO 'pi'@'localhost' WITH GRANT OPTION;"

#Znovunačtení oprávnění
sudo mysql -u root -e "FLUSH PRIVILEGES;"

#Import dat do databáze z data.sql
sudo mysql -u pi -p$PASS Ecowitt_database < data.sql

#Restart Apache pro provedení změn
sudo systemctl restart apache2

#Vytvoření systemd služby
SERVICE_FILE="/etc/systemd/system/my_server.service"
HTML_DIR="/var/www/html"

#Vytvoření obsahu služby
cat <<EOF | sudo tee $SERVICE_FILE > /dev/null
[Unit]
Description=Python Weather API Server
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 $HTML_DIR/API_server_3_10.py
Restart=always
User=pi

[Install]
WantedBy=multi-user.target
EOF

#Spuštění API serveru
/usr/bin/python3 $HTML_DIR/API_server_3_10.py &

#Nastavení oprávnění adresáře /var/www/html
sudo chmod -R 755 $HTML_DIR

#Načtení změn do systému
sudo systemctl daemon-reload

#Spuštění a povolení služby
sudo systemctl start my_server
sudo systemctl enable my_server

echo "Instalace dokončena."

echo "Generované heslo : $PASS"

echo "Heslo si zapište pro zpětné přístupy"
