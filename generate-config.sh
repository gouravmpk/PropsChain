#!/bin/bash
# Generate .well-known/propchain-config.json for the frontend
# 
# This file is served by S3/CloudFront and tells the frontend
# what backend URL to use. It's updated by the deploy script
# whenever the Fargate IP changes.
#
# Usage in deploy.sh:
#   ./generate-config.sh "$FARGATE_IP" "frontend/public"

FARGATE_IP="$1"
OUTPUT_DIR="${2:-frontend/public}"

if [ -z "$FARGATE_IP" ]; then
  echo "Usage: $0 <fargate-ip> [output-dir]"
  exit 1
fi

mkdir -p "$OUTPUT_DIR/.well-known"

cat > "$OUTPUT_DIR/.well-known/propchain-config.json" << EOF
{
  "api_url": "https://$FARGATE_IP:8000",
  "generated_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF

echo "✅ Config generated: $OUTPUT_DIR/.well-known/propchain-config.json"
