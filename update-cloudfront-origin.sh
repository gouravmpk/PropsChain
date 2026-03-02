#!/bin/bash
# =============================================================================
# Update CloudFront Distribution Origin with Fargate IP
# =============================================================================
# This script updates the CloudFront distribution's backend origin
# to point to the current Fargate task IP (which changes on each deploy)
#
# Usage: ./update-cloudfront-origin.sh <FARGATE_IP> <CLOUDFRONT_DIST_ID>
# =============================================================================

set -e

FARGATE_IP="${1}"
CF_DIST_ID="${2}"
AWS_REGION="${AWS_REGION:-ap-south-1}"

if [[ -z "$FARGATE_IP" ]] || [[ -z "$CF_DIST_ID" ]]; then
  echo "Usage: ./update-cloudfront-origin.sh <FARGATE_IP> <CLOUDFRONT_DIST_ID>"
  exit 1
fi

BACKEND_DOMAIN="${FARGATE_IP}:8000"

echo "📡 Updating CloudFront origin to: $BACKEND_DOMAIN"

# Get current distribution config
DIST_CONFIG=$(aws cloudfront get-distribution-config \
  --id "$CF_DIST_ID" \
  --region "$AWS_REGION" \
  --output json)

# Extract ETag (required for updating)
ETAG=$(echo "$DIST_CONFIG" | jq -r '.ETag')

# Find and update the backend origin (the one with HTTPS on port 8000)
UPDATED_CONFIG=$(echo "$DIST_CONFIG" | jq \
  --arg domain "$BACKEND_DOMAIN" \
  '.DistributionConfig.Origins |= map(
    if .CustomOriginConfig and .CustomOriginConfig.HTTPSPort == 8000
    then .DomainName = $domain
    else .
    end
  )' | jq '.DistributionConfig')

# Update the distribution with the new origin
aws cloudfront update-distribution \
  --id "$CF_DIST_ID" \
  --distribution-config "$UPDATED_CONFIG" \
  --if-match "$ETAG" \
  --region "$AWS_REGION" \
  --output json > /dev/null

echo "✅ CloudFront origin updated"
