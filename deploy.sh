#!/bin/bash
# =============================================================================
# PropChain — Full Deploy Script (with API Gateway)
# =============================================================================
# Architecture:
#   Frontend (CloudFront) → API Gateway → Fargate Backend
#   - CloudFront: serves React static files from S3
#   - API Gateway: provides HTTPS endpoint with valid cert, proxies to Fargate
#   - Fargate: runs backend with self-signed HTTPS cert (internal only)
#
# What this does (in order):
#   1. CDK deploy               → creates/updates AWS infrastructure (includes API Gateway)
#   2. Docker build + push      → backend image to ECR
#   3. ECS force-deploy         → restarts containers with the new image
#   4. Get API Gateway URL      → from CloudFormation outputs
#   5. React build + S3 sync    → frontend static files to S3 (with API URL)
#   6. CloudFront invalidate    → clears CDN cache
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

# =============================================================================
# STEP 1 — CDK deploy (infrastructure)
# =============================================================================
if [[ "$APP_ONLY" == "false" ]]; then
  log "Step 1/5 — Deploying CDK stack (infrastructure)..."
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
API_GATEWAY_URL=$(cfn_output "APIGatewayURL")
ECS_SERVICE=$(aws ecs list-services --cluster propchain --region "$AWS_REGION" --query "serviceArns[0]" --output text | awk -F/ '{print $NF}')

log "ECR:              $ECR_URI"
log "S3 Bucket:        $BUCKET"
log "CloudFront:       $CF_URL"
log "API Gateway:      $API_GATEWAY_URL"
log "ECS Service:      $ECS_SERVICE"

# =============================================================================
# STEP 2 — Build + push backend Docker image to ECR
# =============================================================================
if [[ "$INFRA_ONLY" == "false" ]]; then
  log "Step 2/5 — Building backend Docker image..."

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
  log "Step 3/5 — Starting ECS service with new image..."
  aws ecs update-service \
    --cluster propchain \
    --service "$ECS_SERVICE" \
    --desired-count 1 \
    --force-new-deployment \
    --region "$AWS_REGION" \
    --output json > /dev/null
  ok "ECS deployment triggered (takes ~2 minutes to become healthy)"

  # =============================================================================
  # STEP 4 — Build React app with API Gateway URL
  # =============================================================================
  log "Step 4/5 — Building React frontend..."

  cd frontend
  npm ci --silent
  # Build with API Gateway URL passed as environment variable
  VITE_API_URL="$API_GATEWAY_URL" npm run build
  cd ..
  ok "React build complete"

  log "Step 4b/5 — Syncing frontend to S3..."
  aws s3 sync frontend/dist/ "s3://$BUCKET/" \
    --delete \
    --region "$AWS_REGION"
  ok "Frontend synced to S3"

  # =============================================================================
  # STEP 5 — Invalidate CloudFront cache
  # =============================================================================
  log "Step 5/5 — Invalidating CloudFront cache..."
  aws cloudfront create-invalidation \
    --distribution-id "$CF_DIST_ID" \
    --paths "/*" \
    --output json > /dev/null
  ok "CloudFront cache invalidated"

  echo ""
  echo -e "${GREEN}========================================"
  echo -e "  PropChain deployed successfully!"
  echo -e "  Frontend:   $CF_URL"
  echo -e "  API:        $API_GATEWAY_URL"
  echo -e "========================================${NC}"
  echo ""
  warn "NEXT: Fill in secrets at AWS Console → Secrets Manager → 'propchain/config'"
  warn "      Keys to set: MONGODB_URL, JWT_SECRET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
fi
