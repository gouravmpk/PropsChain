#!/bin/bash
# =============================================================================
# PropChain Deployment Status Checker
# =============================================================================
# Shows real-time status of:
#   - CDK Infrastructure
#   - Docker/ECR
#   - ECS Service & Tasks
#   - Fargate IP & Healthcheck
#   - Frontend Config
#   - S3 Sync Status
#   - CloudFront Cache
# =============================================================================
set -e

AWS_REGION="${AWS_REGION:-ap-south-1}"
STACK_NAME="PropChainStack"

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
check() { echo -e "${GREEN}✅${NC}"; }
cross() { echo -e "${RED}❌${NC}"; }
wait() { echo -e "${YELLOW}⏳${NC}"; }

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}PropChain Deployment Status${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# ── 1. CDK Stack Status ────────────────────────────────────────────────────────
echo -n "CDK Infrastructure: "
STACK_STATUS=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null || echo "NOT_FOUND")

if [[ "$STACK_STATUS" == "CREATE_COMPLETE" ]] || [[ "$STACK_STATUS" == "UPDATE_COMPLETE" ]]; then
  check "  ($STACK_STATUS)"
elif [[ "$STACK_STATUS" == *"IN_PROGRESS"* ]]; then
  wait "  ($STACK_STATUS)"
else
  cross "  ($STACK_STATUS)"
fi

# ── 2. ECR Repository ────────────────────────────────────────────────────────
echo -n "Docker/ECR: "
ECR_URI=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`ECRRepository`].OutputValue' \
  --output text)

if [[ -n "$ECR_URI" ]]; then
  IMAGE_COUNT=$(aws ecr describe-images --repository-name propchain --region "$AWS_REGION" --query 'length(imageDetails)' --output text 2>/dev/null || echo "0")
  check "  ($IMAGE_COUNT images in $ECR_URI)"
else
  cross "  (ECR not found)"
fi

# ── 3. ECS Service Status ────────────────────────────────────────────────────
echo -n "ECS Service: "
ECS_SERVICE=$(aws ecs list-services --cluster propchain --region "$AWS_REGION" --query 'serviceArns[0]' --output text 2>/dev/null | awk -F/ '{print $NF}')

if [[ -n "$ECS_SERVICE" ]]; then
  ECS_INFO=$(aws ecs describe-services \
    --cluster propchain \
    --services "$ECS_SERVICE" \
    --region "$AWS_REGION" \
    --query 'services[0].[desiredCount,runningCount,deployments[0].status]' \
    --output text)
  
  DESIRED=$(echo "$ECS_INFO" | awk '{print $1}')
  RUNNING=$(echo "$ECS_INFO" | awk '{print $2}')
  DEPLOY_STATUS=$(echo "$ECS_INFO" | awk '{print $3}')
  
  if [[ "$DESIRED" == "$RUNNING" ]] && [[ "$DEPLOY_STATUS" == "PRIMARY" ]]; then
    check "  ($RUNNING/$DESIRED running, $DEPLOY_STATUS)"
  elif [[ "$DESIRED" != "$RUNNING" ]]; then
    wait "  ($RUNNING/$DESIRED running, rolling out...)"
  else
    cross "  ($RUNNING/$DESIRED running)"
  fi
else
  cross "  (Service not found)"
fi

# ── 4. Fargate Task & IP ──────────────────────────────────────────────────
echo -n "Fargate Task: "
TASK_ARN=$(aws ecs list-tasks --cluster propchain --region "$AWS_REGION" --query 'taskArns[0]' --output text 2>/dev/null)

if [[ -n "$TASK_ARN" ]]; then
  TASK_JSON=$(aws ecs describe-tasks \
    --cluster propchain \
    --tasks "$TASK_ARN" \
    --region "$AWS_REGION" \
    --output json 2>/dev/null)
  
  TASK_STATUS=$(echo "$TASK_JSON" | jq -r '.tasks[0].lastStatus')
  ENI=$(echo "$TASK_JSON" | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId") | .value' 2>/dev/null)
  
  if [[ "$TASK_STATUS" == "PROVISIONING" ]]; then
    wait "  ($TASK_STATUS, waiting for IP...)"
    FARGATE_IP=""
  elif [[ "$TASK_STATUS" == "PENDING" ]]; then
    wait "  ($TASK_STATUS, starting...)"
    FARGATE_IP=""
  elif [[ -n "$ENI" ]] && [[ "$ENI" != "null" ]] && [[ "$ENI" != "" ]]; then
    FARGATE_IP=$(aws ec2 describe-network-interfaces \
      --network-interface-ids "$ENI" \
      --region "$AWS_REGION" \
      --query 'NetworkInterfaces[0].Association.PublicIp' \
      --output text 2>/dev/null)
    
    if [[ -n "$FARGATE_IP" ]] && [[ "$FARGATE_IP" != "None" ]]; then
      if [[ "$TASK_STATUS" == "RUNNING" ]]; then
        check "  ($TASK_STATUS, IP: $FARGATE_IP)"
      else
        wait "  ($TASK_STATUS, IP: $FARGATE_IP)"
      fi
    else
      wait "  ($TASK_STATUS, IP being assigned...)"
      FARGATE_IP=""
    fi
  else
    wait "  ($TASK_STATUS, ENI being attached...)"
    FARGATE_IP=""
  fi
else
  cross "  (No tasks found)"
  FARGATE_IP=""
fi

# ── 5. Backend HTTPS Health ──────────────────────────────────────────────────
echo -n "Backend Health: "
if [[ -n "$FARGATE_IP" ]]; then
  HEALTH=$(curl -sk --connect-timeout 3 https://$FARGATE_IP:8000/api/health 2>/dev/null | grep -o '"status":"ok"' || echo "failed")
  if [[ "$HEALTH" == *"ok"* ]]; then
    check "  (HTTPS responding)"
  else
    cross "  (Not responding)"
  fi
else
  echo -e "${YELLOW}⊘${NC}  (Waiting for IP)"
fi

# ── 6. Frontend Config ────────────────────────────────────────────────────
echo -n "Frontend Config: "
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`FrontendBucketName`].OutputValue' \
  --output text 2>/dev/null)

if [[ -n "$BUCKET" ]]; then
  CONFIG_EXISTS=$(aws s3 ls s3://$BUCKET/.well-known/propchain-config.json --region "$AWS_REGION" 2>/dev/null)
  if [[ -n "$CONFIG_EXISTS" ]]; then
    CONFIG_IP=$(aws s3 cp s3://$BUCKET/.well-known/propchain-config.json - --region "$AWS_REGION" 2>/dev/null | grep -o 'https://[^"]*' | grep -o '[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*' | head -1)
    if [[ -n "$CONFIG_IP" ]]; then
      check "  (Config IP: $CONFIG_IP)"
    else
      cross "  (Config malformed)"
    fi
  else
    cross "  (Config file not found)"
  fi
else
  cross "  (Bucket not found)"
fi

# ── 7. S3 Frontend Files ──────────────────────────────────────────────────
echo -n "S3 Files: "
if [[ -n "$BUCKET" ]]; then
  FILE_COUNT=$(aws s3 ls s3://$BUCKET/ --region "$AWS_REGION" 2>/dev/null | wc -l)
  if [[ "$FILE_COUNT" -gt 0 ]]; then
    check "  ($FILE_COUNT items uploaded)"
  else
    cross "  (No files in bucket)"
  fi
else
  cross "  (Bucket not found)"
fi

# ── 8. CloudFront Cache Status ────────────────────────────────────────────────
echo -n "CloudFront Cache: "
CF_DIST_ID=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
  --output text 2>/dev/null)

if [[ -n "$CF_DIST_ID" ]]; then
  INVALIDATION=$(aws cloudfront list-invalidations \
    --distribution-id "$CF_DIST_ID" \
    --query 'InvalidationList.Items[0].[Id,Status]' \
    --output text 2>/dev/null)
  
  INV_ID=$(echo "$INVALIDATION" | awk '{print $1}')
  INV_STATUS=$(echo "$INVALIDATION" | awk '{print $2}')
  
  if [[ "$INV_STATUS" == "Completed" ]]; then
    check "  (Cache invalidated - $INV_ID)"
  elif [[ "$INV_STATUS" == "InProgress" ]]; then
    wait "  (Invalidating - $INV_ID)"
  else
    cross "  (Status: $INV_STATUS)"
  fi
else
  cross "  (CloudFront not found)"
fi

# ── 9. CloudFront URL ────────────────────────────────────────────────────
echo ""
echo -n "Frontend URL: "
CF_URL=$(aws cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --region "$AWS_REGION" \
  --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontURL`].OutputValue' \
  --output text 2>/dev/null | sed 's|https://||g' | sed 's|http://||g')

if [[ -n "$CF_URL" ]]; then
  check ""
  echo "  🌐 https://$CF_URL"
else
  cross "  (URL not found)"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo ""
