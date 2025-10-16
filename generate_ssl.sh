#!/bin/bash

# Generate self-signed SSL certificate for WSS WebSocket server
# This creates a certificate valid for 365 days

echo "🔐 Generating self-signed SSL certificate for WSS..."

# Create certs directory if it doesn't exist
mkdir -p certs

# Generate private key and certificate
openssl req -x509 -newkey rsa:4096 -nodes \
    -keyout certs/server-key.pem \
    -out certs/server-cert.pem \
    -days 365 \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ SSL certificate generated successfully!"
    echo ""
    echo "📁 Files created:"
    echo "   Certificate: certs/server-cert.pem"
    echo "   Private Key: certs/server-key.pem"
    echo ""
    echo "🚀 To start server with WSS:"
    echo "   python server_ws.py --ssl-cert certs/server-cert.pem --ssl-key certs/server-key.pem"
    echo ""
    echo "⚠️  Note: Self-signed certificates will show browser warnings."
    echo "   For production, use certificates from Let's Encrypt or a CA."
else
    echo "❌ Error generating SSL certificate"
    exit 1
fi
