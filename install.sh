#!/usr/bin/env bash
#
# Server setup for the autotracker app. Prompts before each section so you can
# install/reconfigure just the pieces you need. Re-running is safe (idempotent).
#
# Run as root (or with sudo):  sudo ./install.sh
set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────────────
APP_NAME="autotracker"
DOMAIN="autotracker.emcfunleague.com"
APP_DIR="/var/www/${DOMAIN}/source"
VENV="/var/www/${DOMAIN}/venv/bin"
RUN_USER="www-data"
RUN_GROUP="www-data"
CERTBOT_EMAIL="beau.hall@wikifri.com"

SOCK="/run/gunicorn-${APP_NAME}.sock"
SERVICE="gunicorn-${APP_NAME}.service"
SOCKET_UNIT="gunicorn-${APP_NAME}.socket"
NGINX_SITE="${APP_NAME}"   # /etc/nginx/sites-available/${NGINX_SITE}

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

# Ask a yes/no question (default Yes). Returns success on yes.
# Pass -y / --yes on the command line to auto-confirm every section.
AUTO_YES="false"
[[ "${1:-}" == "-y" || "${1:-}" == "--yes" ]] && AUTO_YES="true"

confirm() {
    if [[ "${AUTO_YES}" == "true" ]]; then
        echo "==> ${1} [auto-yes]"
        return 0
    fi
    local reply
    read -r -p "==> ${1} [Y/n] " reply
    reply="${reply:-Y}"
    [[ "${reply}" =~ ^[Yy]$ ]]
}

# ── gunicorn (socket + service) ─────────────────────────────────────────────
install_gunicorn() {
    echo "  - Writing /etc/systemd/system/${SOCKET_UNIT}"
    cat > "/etc/systemd/system/${SOCKET_UNIT}" <<EOF
[Unit]
Description=gunicorn socket for ${APP_NAME}

[Socket]
ListenStream=${SOCK}
SocketUser=${RUN_USER}
SocketGroup=${RUN_GROUP}
SocketMode=0660

[Install]
WantedBy=sockets.target
EOF

    echo "  - Writing /etc/systemd/system/${SERVICE}"
    cat > "/etc/systemd/system/${SERVICE}" <<EOF
[Unit]
Description=gunicorn daemon for ${APP_NAME}
Requires=${SOCKET_UNIT}
After=network.target

[Service]
User=${RUN_USER}
Group=${RUN_GROUP}
WorkingDirectory=${APP_DIR}
ExecStart=${VENV}/gunicorn \\
          --access-logfile - \\
          --workers 3 \\
          --bind unix:${SOCK} \\
          config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

    echo "  - Reloading systemd, enabling socket, restarting service"
    systemctl daemon-reload
    systemctl enable --now "${SOCKET_UNIT}"
    systemctl restart "${SERVICE}"
}

# ── nginx site ──────────────────────────────────────────────────────────────
install_nginx() {
    echo "  - Writing /etc/nginx/sites-available/${NGINX_SITE}"
    cat > "/etc/nginx/sites-available/${NGINX_SITE}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://unix:${SOCK};
        proxy_set_header Host              \$host;
        proxy_set_header X-Real-IP         \$remote_addr;
        proxy_set_header X-Forwarded-For   \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    echo "  - Symlinking into sites-enabled and reloading nginx"
    ln -sf "/etc/nginx/sites-available/${NGINX_SITE}" "/etc/nginx/sites-enabled/${NGINX_SITE}"
    nginx -t
    systemctl restart nginx
}

# ── TLS via Let's Encrypt (certbot) ─────────────────────────────────────────
install_certbot() {
    if ! command -v certbot >/dev/null 2>&1; then
        echo "  ! certbot is not installed. Install it first, e.g.:" >&2
        echo "        apt install certbot python3-certbot-nginx" >&2
        echo "    then re-run this script (or: certbot --nginx -d ${DOMAIN})." >&2
        return 1
    fi
    echo "  - Requesting/installing certificate for ${DOMAIN}"
    # certbot rewrites the site conf to add the 443 block and the redirect.
    certbot --nginx \
        --non-interactive --agree-tos \
        -m "${CERTBOT_EMAIL}" \
        -d "${DOMAIN}" \
        --redirect
}

# ── Run selected sections ───────────────────────────────────────────────────
if confirm "Install the gunicorn socket + service?"; then
    install_gunicorn
fi

if confirm "Install the nginx site?"; then
    install_nginx
fi

if confirm "Obtain/install a TLS certificate with certbot?"; then
    install_certbot
fi

echo "==> Done."
