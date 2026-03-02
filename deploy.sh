#!/bin/bash
# =============================================================================
# PropChain — Full Deploy Script
# =============================================================================
# What this does (in order):
#   1. CDK deploy  → creates/updates AWS infrastructure
#   2. Docker build + push → backend image to ECR
#   3. ECS force-deploy    → restarts containers with the new image
#   4. React build + S3 sync → frontend static files to S3
#   5. CloudFront invalidate → clears CDN cache so users see the new frontend
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
  # (fine for a hackathon; use default in production) 
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
BACKEND_URL_PARAM=$(cfn_output "BackendURLParameter")
ECS_SERVICE=$(aws ecs list-services --cluster propchain --region "$AWS_REGION" --query "serviceArns[0]" --output text | awk -F/ '{print $NF}')

log "ECR:          $ECR_URI"
log "S3 Bucket:    $BUCKET"
log "CloudFront:   $CF_URL"
log "ECS Service:  $ECS_SERVICE"
log "SSM Param:    $BACKEND_URL_PARAM"

# =============================================================================
# STEP 2 — Build + push backend Docker image to ECR
# =============================================================================
if [[ "$INFRA_ONLY" == "false" ]]; then
  log "Step 2/5 — Building backend Docker image..."

  # Log in to ECR (token valid for 12 hours)
  # aws ecr get-login-password pipes the token to docker login
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
  # desired-count 1: scale up from 0 (infra deploy starts at 0 so CF doesn't wait for image)
  # --force-new-deployment: pull fresh :latest image on every app deploy
  aws ecs update-service \
    --cluster propchain \
    --service "$ECS_SERVICE" \
    --desired-count 1 \
    --force-new-deployment \
    --region "$AWS_REGION" \
    --output json > /dev/null
  ok "ECS deployment triggered (takes ~2 minutes to become healthy)"

  # =============================================================================
  # STEP 4 — Build React app and sync to S3
  # =============================================================================
  log "Step 4/5 — Building React frontend..."

  # Get the Fargate task's public IP (changes on every redeploy)
  TASK_ARN=$(aws ecs list-tasks --cluster propchain --region "$AWS_REGION" \
    --query 'taskArns[0]' --output text)
  ENI=$(aws ecs describe-tasks --cluster propchain --tasks "$TASK_ARN" \
    --region "$AWS_REGION" \
    --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' \
    --output text)
  FARGATE_IP=$(aws ec2 describe-network-interfaces \
    --network-interface-ids "$ENI" --region "$AWS_REGION" \
    --query 'NetworkInterfaces[0].Association.PublicIp' --output text)
  log "Fargate API IP: $FARGATE_IP"

  cd frontend
  # Generate config file with current Fargate IP
  # This will be served at /.well-known/propchain-config.json
  ../generate-config.sh "$FARGATE_IP" "public"
  
  # Build React WITHOUT hardcoding the backend URL
  # Frontend now reads URL from config at runtime (see api.js)
  npm ci --silent
  npm run build
  cd ..
  ok "React build complete"

  log "Step 4b/5 — Updating Parameter Store with new Fargate IP..."
  # Update the SSM Parameter with the new Fargate IP
  # Frontend will fetch this at startup without needing a rebuild
  BACKEND_URL="https://$FARGATE_IP:8000"
  aws ssm put-parameter \
    --name "$BACKEND_URL_PARAM" \
    --value "$BACKEND_URL" \
    --overwrite \
    --region "$AWS_REGION" \
    --output json > /dev/null
  log "Parameter Store updated: $BACKEND_URL"

  log "Step 4c/5 — Syncing frontend to S3..."
  # --delete removes files from S3 that are no longer in the build output
  aws s3 sync frontend/dist/ "s3://$BUCKET/" \
    --delete \
    --region "$AWS_REGION"
  ok "Frontend synced to S3"

  # =============================================================================
  # STEP 5 — Invalidate CloudFront cache
  # =============================================================================
  log "Step 5/5 — Invalidating CloudFront cache..."
  log "Step 5/5 — Invalidating CloudFront cache..."
  # After uploading new files to S3, CloudFront edge nodes still serve cached
  # old files. Invalidating /* forces them to fetch fresh copies from S3.
  aws cloudfront create-invalidation \
    --distribution-id "$CF_DIST_ID" \
    --paths "/*" \
    --output json > /dev/null
  ok "CloudFront cache invalidated"

  echo ""
  echo -e "${GREEN}========================================"
  echo -e "  PropChain deployed successfully!"
  echo -e "  URL: $CF_URL"
  echo -e "========================================${NC}"
  echo ""
  warn "NEXT: Fill in secrets at AWS Console → Secrets Manager → 'propchain/config'"
  warn "      Keys to set: MONGODB_URL, JWT_SECRET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY"
fi
