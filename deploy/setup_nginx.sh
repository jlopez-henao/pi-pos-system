#!/bin/bash
set -e

if [[ "$(uname)" != "Linux" ]]; then
  echo "Error: This deployment script must be run on your Linux EC2 instance, not macOS."
  exit 1
fi

echo "Installing and starting Nginx..."
sudo dnf install nginx -y
sudo systemctl enable --now nginx

echo "Copying Nginx configuration..."
sudo cp deploy/nginx.conf /etc/nginx/conf.d/flask_app.conf
sudo nginx -t
sudo systemctl reload nginx

echo "Setting up Flask background service..."
sudo cp deploy/pi-pos.service /etc/systemd/system/pi-pos.service
sudo systemctl daemon-reload
sudo systemctl enable --now pi-pos.service
sudo systemctl restart pi-pos.service

echo "Deployment complete! Your app is now running 24/7 in the background."
