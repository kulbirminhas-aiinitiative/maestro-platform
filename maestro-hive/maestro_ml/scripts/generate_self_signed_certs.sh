#!/bin/bash
#
# Generate Self-Signed TLS Certificates for Development
# For production, use Let's Encrypt with cert-manager
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
CERTS_DIR="$PROJECT_ROOT/certs"

echo "🔐 Generating Self-Signed TLS Certificates"
echo "=============================================="
echo ""

# Create certs directory
mkdir -p "$CERTS_DIR"

# Generate private key
echo "📝 Generating RSA private key (4096 bits)..."
openssl genrsa -out "$CERTS_DIR/key.pem" 4096

# Generate certificate signing request (CSR)
echo "📝 Generating certificate signing request..."
openssl req -new -key "$CERTS_DIR/key.pem" -out "$CERTS_DIR/csr.pem" \
  -subj "/C=US/ST=California/L=San Francisco/O=Maestro ML/OU=Development/CN=localhost" \
  -addext "subjectAltName=DNS:localhost,DNS:maestro-api,DNS:api.maestro.local,IP:127.0.0.1"

# Generate self-signed certificate (valid for 1 year)
echo "📝 Generating self-signed certificate (365 days)..."
openssl x509 -req -days 365 \
  -in "$CERTS_DIR/csr.pem" \
  -signkey "$CERTS_DIR/key.pem" \
  -out "$CERTS_DIR/cert.pem" \
  -extfile <(printf "subjectAltName=DNS:localhost,DNS:maestro-api,DNS:api.maestro.local,IP:127.0.0.1")

# Set proper permissions
chmod 600 "$CERTS_DIR/key.pem"
chmod 644 "$CERTS_DIR/cert.pem"

echo ""
echo "✅ Certificates generated successfully!"
echo ""
echo "📁 Certificate files:"
echo "   Private key: $CERTS_DIR/key.pem"
echo "   Certificate: $CERTS_DIR/cert.pem"
echo "   CSR:         $CERTS_DIR/csr.pem"
echo ""
echo "📊 Certificate details:"
openssl x509 -in "$CERTS_DIR/cert.pem" -noout -subject -dates -issuer
echo ""
echo "⚠️  Note: This is a self-signed certificate for DEVELOPMENT only."
echo "   For production, use Let's Encrypt or your organization's CA."
echo ""
echo "🚀 To use with Uvicorn:"
echo "   uvicorn main:app --host 0.0.0.0 --port 8443 \\"
echo "     --ssl-keyfile=$CERTS_DIR/key.pem \\"
echo "     --ssl-certfile=$CERTS_DIR/cert.pem"
echo ""
