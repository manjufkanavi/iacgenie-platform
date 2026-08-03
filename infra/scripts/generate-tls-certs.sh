#!/bin/bash
# =============================================================================
# TLS Certificate Generation for Local Development
# =============================================================================
# Generates self-signed TLS certificates for all local services.
# Uses mkcert if available, otherwise falls back to openssl.
#
# Usage:
#   ./generate-tls-certs.sh
#
# Output:
#   - certs/ca.pem, certs/ca-key.pem  (local CA)
#   - certs/fullchain.pem             (certificate chain)
#   - certs/privkey.pem               (private key)
#   - certs/dhparam.pem               (Diffie-Hellman params)
#
# Domains covered:
#   - *.local (covers iacgenie.local, lightsrp.local, infra.local, auth.local)
# =============================================================================

set -euo pipefail

CERT_DIR="certs"
DOMAINS=("iacgenie.local" "lightsrp.local" "infra.local" "auth.local" "localhost")

mkdir -p "$CERT_DIR"

# Generate self-signed certificates using openssl (no external dependencies)
echo "==> Generating self-signed TLS certificates..."

# Generate CA key and certificate
openssl genrsa -out "$CERT_DIR/ca-key.pem" 4096 2>/dev/null
openssl req -new -x509 -key "$CERT_DIR/ca-key.pem" \
  -out "$CERT_DIR/ca.pem" \
  -days 3650 \
  -subj "/C=US/ST=State/L=City/O=IacGenie Dev/CN=IacGenie Local CA" 2>/dev/null

# Generate server private key
openssl genrsa -out "$CERT_DIR/privkey.pem" 4096 2>/dev/null

# Generate SAN certificate
cat > "$CERT_DIR/openssl-san.cnf" <<EOF
[req]
default_bits = 4096
prompt = no
distinguished_name = dn
req_extensions = v3_req

[dn]
C = US
ST = State
L = City
O = IacGenie Dev
CN = *.local

[v3_req]
subjectAltName = @alt_names
basicConstraints = CA:FALSE
keyUsage = digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth, clientAuth

[alt_names]
DNS.1 = *.local
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

openssl req -new -key "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/server.csr" \
  -config "$CERT_DIR/openssl-san.cnf" 2>/dev/null

openssl x509 -req -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.pem" \
  -CAkey "$CERT_DIR/ca-key.pem" \
  -CAcreateserial \
  -out "$CERT_DIR/fullchain.pem" \
  -days 365 \
  -extfile "$CERT_DIR/openssl-san.cnf" \
  -extensions v3_req 2>/dev/null

# Generate DH parameters (2048 bit for reasonable generation time)
echo "==> Generating DH parameters (this may take a minute)..."
openssl dhparam -out "$CERT_DIR/dhparam.pem" 2048 2>/dev/null

# Clean up CSR and config
rm -f "$CERT_DIR/server.csr" "$CERT_DIR/openssl-san.cnf" "$CERT_DIR/ca.srl"

# Set secure permissions
chmod 600 "$CERT_DIR/privkey.pem" "$CERT_DIR/ca-key.pem"
chmod 644 "$CERT_DIR/ca.pem" "$CERT_DIR/fullchain.pem" "$CERT_DIR/dhparam.pem"

echo "==> TLS certificates generated in $CERT_DIR/"
echo "    fullchain.pem  - Server certificate + CA chain"
echo "    privkey.pem    - Private key"
echo "    ca.pem         - CA certificate (for trust)"
echo "    dhparam.pem    - DH parameters"
echo ""
echo "For production, replace these with certificates from a CA (e.g., Let's Encrypt)"
