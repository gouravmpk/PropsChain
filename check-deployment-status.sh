#!/bin/bash
set -euo pipefail

AWS_REGION="${AWS_REGION:-ap-south-1}"
STACK_NAME="${STACK_NAME:-PropChainStack}"
ECS_CLUSTER="${ECS_CLUSTER:-propchain}"

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
ok() { echo -e "${GREEN}✅${NC} $1"; }
bad() { echo -e "${RED}❌${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
info() { echo -e "${BLUE}ℹ️${NC} $1"; }

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PropChain Drift + Health Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

CF_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text)

CF_DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text)

ECS_SERVICE=$(aws ecs list-services \
  --cluster "$ECS_CLUSTER" \
  --region "$AWS_REGION" \
  --query 'serviceArns[0]' \
  --output text | awk -F/ '{print $NF}')

TASK_ARN=$(aws ecs list-tasks \
  --cluster "$ECS_CLUSTER" \
  --service-name "$ECS_SERVICE" \
  --desired-status RUNNING \
  --region "$AWS_REGION" \
  --query 'taskArns[0]' \
  --output text)

if [[ -z "$TASK_ARN" || "$TASK_ARN" == "None" ]]; then
  bad "No running ECS task found in cluster '$ECS_CLUSTER'"
  exit 1
fi

ENI_ID=$(aws ecs describe-tasks \
  --cluster "$ECS_CLUSTER" \
  --tasks "$TASK_ARN" \
  --region "$AWS_REGION" \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
  --output text)

TASK_PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids "$ENI_ID" \
  --region "$AWS_REGION" \
  --query 'NetworkInterfaces[0].Association.PublicIp' \
  --output text)

TASK_DOMAIN="${TASK_PUBLIC_IP}.nip.io"

CF_CONFIG=$(aws cloudfront get-distribution-config --id "$CF_DIST_ID" --region "$AWS_REGION")
API_ORIGIN_ID=$(echo "$CF_CONFIG" | jq -r '.DistributionConfig.CacheBehaviors.Items[]? | select(.PathPattern == "/api/*") | .TargetOriginId' | head -n1)
API_ORIGIN_DOMAIN=$(echo "$CF_CONFIG" | jq -r --arg id "$API_ORIGIN_ID" '.DistributionConfig.Origins.Items[] | select(.Id == $id) | .DomainName')

info "CloudFront URL: $CF_URL"
info "ECS Service: $ECS_SERVICE"
info "Running Task: $TASK_ARN"
info "Task Public IP: $TASK_PUBLIC_IP"
info "Expected API Origin: $TASK_DOMAIN"
info "Current API Origin:  $API_ORIGIN_DOMAIN"

if [[ "$API_ORIGIN_DOMAIN" == "$TASK_DOMAIN" ]]; then
  ok "CloudFront /api/* origin matches current ECS task"
else
  bad "CloudFront /api/* origin drift detected"
fi

HEALTH_STATUS=$(curl -sS -o /tmp/propchain-health-check.json -w "%{http_code}" "${CF_URL%/}/api/health" || true)
HEALTH_BODY=$(cat /tmp/propchain-health-check.json 2>/dev/null || echo "")

if [[ "$HEALTH_STATUS" == "200" ]]; then
  ok "Health check passed: ${CF_URL%/}/api/health (HTTP 200)"
else
  bad "Health check failed: ${CF_URL%/}/api/health (HTTP $HEALTH_STATUS)"
  warn "Response body: $HEALTH_BODY"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo ""
