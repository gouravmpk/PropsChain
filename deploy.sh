#!/bin/bash
# =============================================================================
# PropChain — Full Deploy Script (Simplified)
# =============================================================================
# Architecture:
#   Frontend (CloudFront) → Fargate Backend (HTTP)
#   - CloudFront: serves React static files from S3
#   - CloudFront /api/* behavior: proxies to Fargate HTTP endpoint 
#   - Fargate: runs backend with HTTP (port 8000)
#
# What this does (in order):
#   1. CDK deploy               → creates/updates AWS infrastructure
#   2. Docker build + push      → backend image to ECR
#   3. ECS force-deploy         → restarts containers with the new image
#   4. Get Fargate IP           → wait for task to get IP address
#   5. Update CloudFront origin → point /api/* to Fargate IP:8000
#   6. React build + S3 sync    → frontend static files to S3
#   7. CloudFront invalidate    → clears CDN cache
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - Docker running
#   - Node.js + npm installed
#   - Python 3.12 + pip installed
#
# Usage:
#   ./deploy.sh                  # deploy everything
#   ./deploy.sh --infra-only     # only run CDK (no Docker/frontend)
#   ./deploy.sh --app-only       # skip CDK, only push image + frontend
# =============================================================================
set -e  # exit on any error

AWS_REGION="${AWS_REGION:-ap-south-1}"
AWS_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
STACK_NAME="PropChainStack"

# ── Colors for readable output ────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
log()  { echo -e "${BLUE}[deploy]${NC} $1"; }
ok()   { echo -e "${GREEN}[done]${NC} $1"; }
warn() { echo -e "${YELLOW}[warn]${NC} $1"; }

INFRA_ONLY=false; APP_ONLY=false
for arg in "$@"; do
  [[ "$arg" == "--infra-only" ]] && INFRA_ONLY=true
  [[ "$arg" == "--app-only" ]]   && APP_ONLY=true
done

# ── Helper: read CloudFormation output value ──────────────────────────────────
cfn_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text --region "$AWS_REGION"
}
# ── Helper: get Fargate task public IP (latest running task) ─────────────────
get_fargate_public_ip() {
  local task_arns_json task_arn eni_id
  task_arns_json=$(aws ecs list-tasks --cluster propchain --region "$AWS_REGION" --desired-status RUNNING --output json 2>/dev/null)
  task_arn=$(echo "$task_arns_json" | jq -r '.taskArns[0]')
  [[ -z "$task_arn" || "$task_arn" == "None" ]] && return 1

  # Prefer newest running task during rolling deploys
  if [[ $(echo "$task_arns_json" | jq '.taskArns | length') -gt 1 ]]; then
    task_arn=$(echo "$task_arns_json" | jq -r '.taskArns[]' | \
      xargs aws ecs describe-tasks --cluster propchain --region "$AWS_REGION" --tasks | \
      jq -r '.tasks | sort_by(.startedAt) | last | .taskArn')
  fi

  eni_id=$(aws ecs describe-tasks --cluster propchain --tasks "$task_arn" --region "$AWS_REGION" \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text 2>/dev/null)
  [[ -z "$eni_id" || "$eni_id" == "None" ]] && return 1

  aws ec2 describe-network-interfaces --network-interface-ids "$eni_id" --region "$AWS_REGION" \
    --query 'NetworkInterfaces[0].Association.PublicIp' --output text 2>/dev/null
}

# ── Helper: update CloudFront origin ─────────────────────────────────────────────
update_cloudfront_origin() {
  local fargate_ip="$1"
  local dist_id="$2"
  local backend_domain api_origin_id

  # CloudFront custom origins require a DNS name, not a raw IP
  backend_domain="${fargate_ip}.nip.io"
  
  # Get current CloudFront config
  local config_json
  config_json=$(aws cloudfront get-distribution-config --id "$dist_id" --region "$AWS_REGION")
  local etag
  etag=$(echo "$config_json" | jq -r '.ETag')

  # Find the origin used by /api/* behavior
  api_origin_id=$(echo "$config_json" | jq -r '.DistributionConfig.CacheBehaviors.Items[]? | select(.PathPattern == "/api/*") | .TargetOriginId' | head -n1)
  if [[ -z "$api_origin_id" || "$api_origin_id" == "null" ]]; then
    warn "Could not find CloudFront /api/* behavior origin"
    return 1
  fi
  
  # Update only the /api/* origin domain in config JSON
  local updated_config
  updated_config=$(echo "$config_json" | jq --arg origin_id "$api_origin_id" --arg domain "$backend_domain" '
    .DistributionConfig.Origins.Items |= map(
      if .Id == $origin_id then
        .DomainName = $domain
      else . end
    ) |
    .DistributionConfig
  ')
  
  # Update CloudFront distribution
  aws cloudfront update-distribution \
    --id "$dist_id" \
    --if-match "$etag" \
    --distribution-config "$updated_config" \
    --region "$AWS_REGION" \
    --output json > /dev/null
}

# ── Helper: wait for API health via CloudFront ───────────────────────────────
wait_for_api_health() {
  local base_url="$1"
  local max_attempts="${2:-120}"
  local attempt=1
  local health_url="${base_url%/}/api/health"

  while [[ $attempt -le $max_attempts ]]; do
    local status
    status=$(curl -s -o /tmp/propchain-health.json -w "%{http_code}" "$health_url" || true)

    if [[ "$status" == "200" ]]; then
      ok "API health check passed (200): $health_url"
      return 0
    fi

    log "Waiting for API health ($attempt/$max_attempts): HTTP $status"
    sleep 5
    attempt=$((attempt + 1))
  done

  warn "API health check failed at: $health_url"
  warn "Last response body: $(cat /tmp/propchain-health.json 2>/dev/null || echo 'n/a')"
  return 1
}
# =============================================================================
# STEP 1 — CDK deploy (infrastructure)
# =============================================================================
if [[ "$APP_ONLY" == "false" ]]; then
  log "Step 1/7 — Deploying CDK stack (infrastructure)..."
  cd "$(dirname "$0")/infra"

  # Create/activate virtualenv for CDK
  [[ ! -d ".venv" ]] && python3 -m venv .venv
  source .venv/bin/activate
  pip install -q -r requirements.txt

  # cdk bootstrap: one-time setup per account/region.
  # Creates an S3 bucket + ECR repo that CDK uses internally to stage assets.
  # Safe to run every time — it's idempotent.
  cdk bootstrap "aws://$AWS_ACCOUNT/$AWS_REGION" -c account="$AWS_ACCOUNT" -c region="$AWS_REGION"

  # cdk deploy --require-approval never → don't prompt for security group changes
  cdk deploy "$STACK_NAME" \
    --require-approval never \
    -c account="$AWS_ACCOUNT" \
    -c region="$AWS_REGION"

  deactivate
  cd ..
  ok "CDK stack deployed"
fi

# ── Read outputs from the deployed stack ──────────────────────────────────────
ECR_URI=$(cfn_output "ECRRepository")
BUCKET=$(cfn_output "FrontendBucketName")
CF_DIST_ID=$(cfn_output "CloudFrontDistributionId")
CF_URL=$(cfn_output "CloudFrontURL")
ECS_SERVICE=$(aws ecs list-services --cluster propchain --region "$AWS_REGION" --query "serviceArns[0]" --output text | awk -F/ '{print $NF}')

log "ECR:              $ECR_URI"
log "S3 Bucket:        $BUCKET"
log "CloudFront:       $CF_URL"
log "ECS Service:      $ECS_SERVICE"

# =============================================================================
# STEP 2 — Build + push backend Docker image to ECR
# =============================================================================
if [[ "$INFRA_ONLY" == "false" ]]; then
  log "Step 2/7 — Building backend Docker image..."

  # Log in to ECR (token valid for 12 hours)
  aws ecr get-login-password --region "$AWS_REGION" | \
    docker login --username AWS --password-stdin "$ECR_URI"

  cd backend
  # Build: --platform linux/amd64 is required when building on Apple Silicon (M1/M2)
  # ECS Fargate runs on x86_64 — without this flag, the image won't start on Fargate
  docker build --platform linux/amd64 -t propchain-backend:latest .

  # Tag with ECR URI and push
  docker tag propchain-backend:latest "$ECR_URI:latest"
  docker push "$ECR_URI:latest"
  cd ..
  ok "Backend image pushed to ECR"

  # =============================================================================
  # STEP 3 — Force ECS to redeploy with the new image
  # =============================================================================
  log "Step 3/7 — Starting ECS service with new image..."
  aws ecs update-service \
    --cluster propchain \
    --service "$ECS_SERVICE" \
    --desired-count 1 \
    --force-new-deployment \
    --region "$AWS_REGION" \
    --output json > /dev/null
  ok "ECS deployment triggered (takes ~2 minutes to become healthy)"

  log "Step 3b/7 — Waiting for ECS service to become stable..."
  aws ecs wait services-stable \
    --cluster propchain \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION"
  ok "ECS service is stable"

  # =============================================================================
  # STEP 4 — Wait for Fargate task to get IP
  # =============================================================================
  log "Step 4/7 — Waiting for Fargate task public IP..."
  
  # Wait up to 5 minutes for task to get a public IP
  for i in {1..60}; do
    FARGATE_IP=$(get_fargate_public_ip 2>/dev/null || echo "")
    if [[ -n "$FARGATE_IP" && "$FARGATE_IP" != "None" ]]; then
      ok "Fargate task public IP: $FARGATE_IP"
      break
    fi
    
    if [[ $i -eq 60 ]]; then
      warn "Timeout waiting for Fargate public IP. Check ECS console."
      exit 1
    fi
    
    sleep 5
  done

  # =============================================================================
  # STEP 5 — Update CloudFront origin to point to Fargate
  # =============================================================================
  log "Step 5/7 — Updating CloudFront origin to Fargate IP..."
  update_cloudfront_origin "$FARGATE_IP" "$CF_DIST_ID"
  ok "CloudFront updated to route /api/* to ${FARGATE_IP}.nip.io:8000"

  # =============================================================================
  # STEP 6 — Build React app (no env vars needed)
  # =============================================================================
  log "Step 6/7 — Building React frontend..."

  cd frontend
  npm ci --silent
  # Build frontend (CloudFront handles /api/* routing automatically)
  npm run build
  cd ..
  ok "React build complete"

  log "Step 6b/7 — Syncing frontend to S3..."
  aws s3 sync frontend/dist/ "s3://$BUCKET/" \
    --delete \
    --region "$AWS_REGION"
  ok "Frontend synced to S3"

  # =============================================================================
  # STEP 7 — Invalidate CloudFront cache
  # =============================================================================
  log "Step 7/7 — Invalidating CloudFront cache..."
  aws cloudfront create-invalidation \
    --distribution-id "$CF_DIST_ID" \
    --paths "/*" \
    --output json > /dev/null
  ok "CloudFront cache invalidated"

  # =============================================================================
  # STEP 8 — Post-deploy health check (must be 200)
  # =============================================================================
  log "Step 8/8 — Verifying API health through CloudFront..."
  wait_for_api_health "$CF_URL" 120

  echo ""
  echo -e "${GREEN}========================================"
  echo -e "  PropChain deployed successfully!"
  echo -e "  Frontend URL: $CF_URL"
  echo -e "  Backend IP:   $FARGATE_IP:8000 (via CloudFront)"
  echo -e "========================================${NC}"
  echo ""
  warn "NEXT: Fill in secrets at AWS Console → Secrets Manager → 'propchain/config'"
  warn "      Keys to set: MONGODB_URL, JWT_SECRET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
fi
