#!/usr/bin/env bash
#
# One-time server setup for the autotracker app.
# Installs the gunicorn systemd socket + service and the nginx site,
# then enables and starts everything. Re-running is safe (idempotent).
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

# TLS: set ENABLE_SSL=false to skip certbot and serve HTTP only.
# certbot's nginx plugin adds the 443 server block + HTTP->HTTPS redirect to the
# site conf and installs an auto-renewal timer.
ENABLE_SSL="true"
CERTBOT_EMAIL="beau.hall@wikifri.com"

SOCK="/run/gunicorn-${APP_NAME}.sock"
SERVICE="gunicorn-${APP_NAME}.service"
SOCKET_UNIT="gunicorn-${APP_NAME}.socket"
NGINX_SITE="${APP_NAME}"   # /etc/nginx/sites-available/${NGINX_SITE}

if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root (use sudo)." >&2
    exit 1
fi

# ── gunicorn socket ─────────────────────────────────────────────────────────
echo "==> Writing /etc/systemd/system/${SOCKET_UNIT}"
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

# ── gunicorn service ────────────────────────────────────────────────────────
echo "==> Writing /etc/systemd/system/${SERVICE}"
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

# ── nginx site ──────────────────────────────────────────────────────────────
echo "==> Writing /etc/nginx/sites-available/${NGINX_SITE}"
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

echo "==> Enabling nginx site (symlinking into sites-enabled)"
ln -sf "/etc/nginx/sites-available/${NGINX_SITE}" "/etc/nginx/sites-enabled/${NGINX_SITE}"

# ── Reload / enable / start ─────────────────────────────────────────────────
echo "==> Reloading systemd and starting the gunicorn socket"
systemctl daemon-reload
systemctl enable --now "${SOCKET_UNIT}"
# Restart the service so it picks up any new code/config if already running.
systemctl restart "${SERVICE}"

echo "==> Testing nginx config"
nginx -t

echo "==> Restarting nginx"
systemctl restart nginx

# ── TLS via Let's Encrypt (certbot) ─────────────────────────────────────────
if [[ "${ENABLE_SSL}" == "true" ]]; then
    echo "==> Provisioning TLS certificate with certbot for ${DOMAIN}"
    if ! command -v certbot >/dev/null 2>&1; then
        echo "certbot is not installed. Install it first, e.g.:" >&2
        echo "    apt install certbot python3-certbot-nginx" >&2
        echo "then re-run this script (or run: certbot --nginx -d ${DOMAIN})." >&2
        exit 1
    fi
    # certbot rewrites the site conf to add the 443 block and the redirect.
    certbot --nginx \
        --non-interactive --agree-tos \
        -m "${CERTBOT_EMAIL}" \
        -d "${DOMAIN}" \
        --redirect
    echo "==> Done. ${APP_NAME} is served at https://${DOMAIN}/ via ${SOCK}"
else
    echo "==> Skipping TLS (ENABLE_SSL=${ENABLE_SSL})."
    echo "==> Done. ${APP_NAME} is served at http://${DOMAIN}/ via ${SOCK}"
fi
