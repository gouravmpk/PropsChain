#!/bin/bash

# PropChain Deployment Status Check
# This script checks the status of all deployed services

set -e

REGION="ap-south-1"
CLUSTER="propchain"
SERVICE="PropChainService"
S3_BUCKET="propchain-frontend-264982087490"
ACCOUNT_ID="264982087490"

echo "🔍 PropChain Deployment Status Check"
echo "=================================="
echo ""

# Check ECS Task Status
echo "📦 ECS Task Status:"
TASK_ARN=$(aws ecs list-tasks --cluster $CLUSTER --region $REGION --query 'taskArns[0]' --output text 2>/dev/null || echo "")

if [ -z "$TASK_ARN" ]; then
    echo "❌ No running tasks found"
else
    TASK_STATUS=$(aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ARN --region $REGION | jq -r '.tasks[0].lastStatus')
    echo "✅ Task Status: $TASK_STATUS"
    echo "   ARN: $TASK_ARN"
fi
echo ""

# Get Public IP
echo "🌐 Backend Service:"
if [ -n "$TASK_ARN" ]; then
    ENI=$(aws ecs describe-tasks --cluster $CLUSTER --tasks $TASK_ARN --region $REGION | jq -r '.tasks[0].attachments[0].details[] | select(.name=="networkInterfaceId") | .value')
    PUBLIC_IP=$(aws ec2 describe-network-interfaces --network-interface-ids $ENI --region $REGION | jq -r '.NetworkInterfaces[0].Association.PublicIp')
    
    echo "✅ Fargate Public IP: $PUBLIC_IP"
    
    # Test Health Endpoint
    HEALTH=$(curl -s http://$PUBLIC_IP:8000/health 2>/dev/null || echo '{"status":"error"}')
    echo "   Health Status: $HEALTH"
else
    echo "⚠️  Cannot check Fargate IP (no running task)"
fi
echo ""

# Check CloudFront Distribution
echo "📡 CloudFront Distribution:"
CF_DOMAIN=$(aws cloudfront list-distributions --region $REGION | jq -r '.DistributionList.Items[0].DomainName')
CF_STATUS=$(aws cloudfront list-distributions --region $REGION | jq -r '.DistributionList.Items[0].Status')
echo "✅ Domain: $CF_DOMAIN"
echo "   Status: $CF_STATUS"
echo "   URL: https://$CF_DOMAIN"
echo ""

# Check S3 Frontend Files
echo "📦 S3 Frontend Files:"
FILE_COUNT=$(aws s3 ls s3://$S3_BUCKET/ --recursive | wc -l)
echo "✅ Files Uploaded: $FILE_COUNT"
aws s3 ls s3://$S3_BUCKET/ --recursive | awk '{print "   " $4}' | head -10
echo ""

# ECS Service Status
echo "⚙️  ECS Service Details:"
SERVICE_INFO=$(aws ecs describe-services --cluster $CLUSTER --services $SERVICE --region $REGION | jq '.services[0]')
echo "   Service Status: $(echo $SERVICE_INFO | jq -r '.status // "N/A"')"
echo "   Desired Count: $(echo $SERVICE_INFO | jq -r '.desiredCount // "N/A"')"
echo ""

# ECR Image Status
echo "🐳 ECR Backend Image:"
ECR_IMAGES=$(aws ecr list-images --repository-name propchain-backend --region $REGION | jq '.imageIds | length')
LATEST_IMAGE=$(aws ecr list-images --repository-name propchain-backend --region $REGION | jq -r '.imageIds[-1].imageTag // "N/A"')
echo "✅ Total Images: $ECR_IMAGES"
echo "   Latest Tag: $LATEST_IMAGE"
echo ""

echo "=================================="
echo "✅ Deployment Status Check Complete"
echo ""
echo "Frontend URL: https://$CF_DOMAIN"
if [ -n "$PUBLIC_IP" ]; then
    echo "Backend API: http://$PUBLIC_IP:8000"
fi
