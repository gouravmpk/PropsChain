"""
PropChain Infrastructure Stack (Hackathon Edition)
====================================================
Lean setup — no ALB, no VPC, no NAT Gateway.

Resources:
  1. ECR Repository       — Docker image storage
  2. Secrets Manager      — encrypted app config
  3. IAM Roles            — execution role + task role (Bedrock access)
  4. ECS Cluster          — Fargate control plane
  5. Fargate Service      — public IP, no load balancer
  6. S3 Bucket            — React static files
  7. CloudFront           — HTTPS CDN for frontend static files
  8. API Gateway          — HTTPS endpoint for backend API (proxies to Fargate)
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ecr as ecr,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_s3 as s3,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_ec2 as ec2,
    aws_ssm as ssm,
    aws_apigateway as apigw,
)
from constructs import Construct


class PropChainStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ──────────────────────────────────────────────────────────────────────
        # 1. ECR Repository
        # ──────────────────────────────────────────────────────────────────────
        backend_repo = ecr.Repository(
            self,
            "BackendRepo",
            repository_name="propchain-backend",
            image_scan_on_push=True,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                ecr.LifecycleRule(max_image_count=5, description="Keep last 5 images")
            ],
        )

        # ──────────────────────────────────────────────────────────────────────
        # 2. Secrets Manager
        # After deploy: AWS Console -> Secrets Manager -> "propchain/config"
        # Fill in: MONGODB_URL, JWT_SECRET, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
        # ──────────────────────────────────────────────────────────────────────
        app_secrets = secretsmanager.Secret(
            self,
            "PropChainSecrets",
            secret_name="propchain/config",
            description="PropChain app secrets",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"MONGODB_URL":"FILL_ME","JWT_SECRET":"FILL_ME","AWS_ACCESS_KEY_ID":"FILL_ME","AWS_SECRET_ACCESS_KEY":"FILL_ME"}',
                generate_string_key="_placeholder",
            ),
        )

        # ──────────────────────────────────────────────────────────────────────
        # 3. IAM Roles
        # execution_role: used by ECS agent to pull image + read secrets
        # task_role:      used by your app code at runtime (Bedrock calls)
        # ──────────────────────────────────────────────────────────────────────
        execution_role = iam.Role(
            self,
            "PropChainExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )
        backend_repo.grant_pull(execution_role)
        app_secrets.grant_read(execution_role)

        task_role = iam.Role(
            self,
            "PropChainTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            description="Runtime role for PropChain Fargate tasks - grants Bedrock access",
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowBedrockNovaPro",
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel", "bedrock:Converse"],
                resources=[
                    "arn:aws:bedrock:ap-south-1::foundation-model/apac.amazon.nova-pro-v1:0",
                    "arn:aws:bedrock:ap-south-1::foundation-model/amazon.nova-pro-v1:0",
                ],
            )
        )
        task_role.add_to_policy(
            iam.PolicyStatement(
                sid="AllowReadSecrets",
                effect=iam.Effect.ALLOW,
                actions=["secretsmanager:GetSecretValue"],
                resources=[app_secrets.secret_arn],
            )
        )

        # ──────────────────────────────────────────────────────────────────────
        # 4. ECS Cluster
        # Uses the default VPC
        # ──────────────────────────────────────────────────────────────────────
        default_vpc = ec2.Vpc.from_lookup(self, "DefaultVpc", is_default=True)

        cluster = ecs.Cluster(
            self,
            "PropChainCluster",
            vpc=default_vpc,
            cluster_name="propchain",
        )

        # ──────────────────────────────────────────────────────────────────────
        # 5. Fargate Task + Service (no ALB — public IP directly on the task)
        # ──────────────────────────────────────────────────────────────────────
        task_def = ecs.FargateTaskDefinition(
            self,
            "PropChainTaskDef",
            cpu=512,
            memory_limit_mib=1024,
            task_role=task_role,
            execution_role=execution_role,
        )

        container = task_def.add_container(
            "BackendContainer",
            image=ecs.ContainerImage.from_ecr_repository(backend_repo, tag="latest"),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="propchain"),
            environment={
                "BEDROCK_REGION": "ap-south-1",
                "BEDROCK_MODEL": "apac.amazon.nova-pro-v1:0",
                "ENVIRONMENT": "production",
            },
            secrets={
                "MONGODB_URL":          ecs.Secret.from_secrets_manager(app_secrets, "MONGODB_URL"),
                "JWT_SECRET":           ecs.Secret.from_secrets_manager(app_secrets, "JWT_SECRET"),
                "AWS_ACCESS_KEY_ID":    ecs.Secret.from_secrets_manager(app_secrets, "AWS_ACCESS_KEY_ID"),
                "AWS_SECRET_ACCESS_KEY":ecs.Secret.from_secrets_manager(app_secrets, "AWS_SECRET_ACCESS_KEY"),
            },
            health_check=ecs.HealthCheck(
                command=["CMD-SHELL", "curl -sk https://localhost:8000/api/health || exit 1"],
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5),
                retries=3,
                start_period=Duration.seconds(60),
            ),
        )
        container.add_port_mappings(ecs.PortMapping(container_port=8000))

        # Security group: allow inbound 8000 from CloudFront IP ranges only
        # For simplicity we open 8000 to all — CloudFront will be the only caller
        # in practice (frontend always goes through CF). Tighten post-hackathon.
        sg = ec2.SecurityGroup(
            self,
            "PropChainSG",
            vpc=default_vpc,
            description="PropChain Fargate task - allow port 8000",
            allow_all_outbound=True,
        )
        sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(8000), "FastAPI")

        # desired_count=0: deploy the service definition but start NO tasks.
        # After pushing the Docker image, run:
        #   aws ecs update-service --cluster propchain --service PropChainService --desired-count 1
        # The deploy script handles this automatically in --app-only mode.
        fargate_service = ecs.FargateService(
            self,
            "PropChainService",
            cluster=cluster,
            task_definition=task_def,
            desired_count=0,          # start with 0 tasks — no image yet
            assign_public_ip=True,
            security_groups=[sg],
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            min_healthy_percent=0,
        )

        # ──────────────────────────────────────────────────────────────────────
        # 6. S3 Bucket — React frontend static files
        # ──────────────────────────────────────────────────────────────────────
        frontend_bucket = s3.Bucket(
            self,
            "FrontendBucket",
            bucket_name=f"propchain-frontend-{self.account}",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )

        # ──────────────────────────────────────────────────────────────────────
        # 7. CloudFront Distribution
        # Serves frontend React app from S3 (static files only)
        # API Gateway handles all /api/* requests (separate endpoint)
        # ──────────────────────────────────────────────────────────────────────
        distribution = cloudfront.Distribution(
            self,
            "PropChainCDN",
            comment="PropChain - React frontend CDN",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3BucketOrigin.with_origin_access_control(
                    frontend_bucket,
                ),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                cache_policy=cloudfront.CachePolicy.CACHING_OPTIMIZED,
                compress=True,
            ),
            # SPA routing: serve index.html for unknown paths (React Router handles them)
            error_responses=[
                cloudfront.ErrorResponse(
                    http_status=403,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
                cloudfront.ErrorResponse(
                    http_status=404,
                    response_http_status=200,
                    response_page_path="/index.html",
                    ttl=Duration.seconds(0),
                ),
            ],
            price_class=cloudfront.PriceClass.PRICE_CLASS_ALL,
        )

        # ──────────────────────────────────────────────────────────────────────
        # 8. API Gateway
        # Provides HTTPS endpoint with valid AWS-managed certificate
        # Proxies requests to Fargate backend (handles self-signed cert internally)
        # ──────────────────────────────────────────────────────────────────────
        api = apigw.RestApi(
            self,
            "PropChainAPI",
            rest_api_name="propchain-api",
            description="PropChain Backend API",
            deploy_options=apigw.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
        )

        # Create /api resource and proxy all requests to it
        api_resource = api.root.add_resource("api")
        
        # HTTP integration to Fargate backend
        # Backend runs on https://172.31.43.122:8000 with self-signed cert
        backend_integration = apigw.HttpIntegration(
            url="https://172.31.43.122:8000/"
        )

        # Add proxy resource: /api/{proxy+} routes all to backend
        proxy_resource = api_resource.add_resource("{proxy+}")
        proxy_resource.add_method(
            "ANY",
            backend_integration,
            method_responses=[apigw.MethodResponse(status_code="200")]
        )
        
        # Handle OPTIONS preflight for /api/{proxy+}
        proxy_resource.add_method(
            "OPTIONS",
            backend_integration,
            method_responses=[apigw.MethodResponse(status_code="200")]
        )

        # Also handle /api directly
        api_resource.add_method(
            "ANY",
            backend_integration,
            method_responses=[apigw.MethodResponse(status_code="200")]
        )
        
        # Handle OPTIONS preflight for /api
        api_resource.add_method(
            "OPTIONS",
            backend_integration,
            method_responses=[apigw.MethodResponse(status_code="200")]
        )
        
        # Enable CORS on the API
        api.root.add_method(
            "OPTIONS",
            backend_integration,
            method_responses=[apigw.MethodResponse(status_code="200")]
        )

        # ──────────────────────────────────────────────────────────────────────
        # Outputs
        # ──────────────────────────────────────────────────────────────────────
        CfnOutput(self, "CloudFrontURL",
            value=f"https://{distribution.distribution_domain_name}",
            description="Frontend URL (React app from CloudFront)",
        )
        CfnOutput(self, "APIGatewayURL",
            value=api.url,
            description="API Gateway endpoint (valid HTTPS cert). Frontend calls this for /api/*",
        )
        CfnOutput(self, "ECRRepository",
            value=backend_repo.repository_uri,
            description="ECR repo - push Docker image here",
        )
        CfnOutput(self, "FrontendBucketName",
            value=frontend_bucket.bucket_name,
            description="S3 bucket - sync React build here",
        )
        CfnOutput(self, "SecretARN",
            value=app_secrets.secret_arn,
            description="Fill in secrets here after deploy",
        )
        CfnOutput(self, "CloudFrontDistributionId",
            value=distribution.distribution_id,
            description="CloudFront ID - for cache invalidation",
        )
        CfnOutput(self, "ECSClusterName",
            value=cluster.cluster_name,
            description="ECS cluster name - for deploy script",
        )
