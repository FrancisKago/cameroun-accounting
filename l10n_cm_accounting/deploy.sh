#!/bin/bash
# Script d'automatisation du déploiement Odoo 17 + l10n_cm_accounting sous Ubuntu 24.04 avec Docker
# Usage : ./deploy.sh

set -e

# 1. Installer Docker et Docker Compose si absents
if ! command -v docker &> /dev/null; then
    echo "[INFO] Installation de Docker..."
    sudo apt update && sudo apt install -y docker.io
    sudo systemctl enable --now docker
    sudo usermod -aG docker $USER
fi
if ! command -v docker-compose &> /dev/null; then
    echo "[INFO] Installation de Docker Compose..."
    sudo apt install -y docker-compose
fi

# 2. Préparer l'arborescence
mkdir -p odoo/custom_addons
cp -r ./l10n_cm_accounting odoo/custom_addons/
cd odoo

# 3. Générer docker-compose.yml
cat > docker-compose.yml <<EOF
version: '3.1'
services:
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - odoo-db-data:/var/lib/postgresql/data
  odoo:
    image: odoo:17.0
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    volumes:
      - ./custom_addons:/mnt/extra-addons
      - ./odoo.conf:/etc/odoo/odoo.conf
      - ./custom_addons/l10n_cm_accounting:/mnt/extra-addons/l10n_cm_accounting
    command: >
      bash -c "pip3 install -r /mnt/extra-addons/l10n_cm_accounting/requirements.txt && odoo -c /etc/odoo/odoo.conf"
volumes:
  odoo-db-data:
EOF

# 4. Générer odoo.conf
cat > odoo.conf <<EOF
[options]
addons_path = /mnt/extra-addons
data_dir = /var/lib/odoo
db_host = db
db_port = 5432
db_user = odoo
db_password = odoo
admin_passwd = admin
log_level = info
EOF

# 5. Lancer les conteneurs
sudo docker-compose up -d

echo "[OK] Odoo lancé sur http://localhost:8069"
echo "Créez votre base et activez le module l10n_cm_accounting."
