#!/bin/bash
set -e

echo "Installing and starting Nginx..."
sudo dnf install nginx -y
sudo systemctl enable --now nginx

echo "Copying Nginx configuration..."
sudo cp deploy/nginx.conf /etc/nginx/conf.d/flask_app.conf

echo "Testing and reloading Nginx..."
sudo nginx -t
sudo systemctl reload nginx

echo "Nginx setup complete!"
