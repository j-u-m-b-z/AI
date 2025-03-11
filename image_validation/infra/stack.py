import pulumi
import pulumi_aws as aws
import json

class HumanImageValidationStack:
    def __init__(self, provider=None, resource_prefix="human-image-validation"):
        # Common resource options to pass the provider to all resources
        self.resource_options = None
        if provider:
            self.resource_options = pulumi.ResourceOptions(provider=provider)
        
        # Store the resource prefix for consistent naming
        self.prefix = resource_prefix
        
        # Common tags for all resources
        self.tags = {
            "Project": "ImageValidation",
            "Environment": "Development",
            "ManagedBy": "Pulumi"
        }
            
        # ✅ 1. S3 Bucket for Image Storage
        self.image_bucket = aws.s3.Bucket(f"{self.prefix}-image-bucket",
            tags=self.tags,
            opts=self.resource_options
        )

        # Add ownership controls for the image bucket
        aws.s3.BucketOwnershipControls(f"{self.prefix}-image-bucket-ownership",
            bucket=self.image_bucket.id,
            rule={
                "object_ownership": "BucketOwnerPreferred"
            },
            opts=self.resource_options
        )

        # ✅ 2. IAM Role for Lambda
        self.lambda_role = aws.iam.Role(f"{self.prefix}-lambda-role",
            assume_role_policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": { "Service": "lambda.amazonaws.com" }
                }]
            }),
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 3. Attach Policies to Lambda Role
        aws.iam.RolePolicyAttachment(f"{self.prefix}-lambda-basic-exec",
            role=self.lambda_role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
            opts=self.resource_options
        )
        
        # Add permissions for S3, DynamoDB, Rekognition, SNS, and SageMaker
        lambda_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject",
                        "s3:PutObject",
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "rekognition:DetectLabels",
                        "sns:Publish",
                        "sagemaker:CreateTrainingJob",
                        "sagemaker:InvokeEndpoint"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        lambda_policy = aws.iam.Policy(f"{self.prefix}-lambda-policy",
            policy=json.dumps(lambda_policy_document),
            tags=self.tags,
            opts=self.resource_options
        )
        
        aws.iam.RolePolicyAttachment(f"{self.prefix}-lambda-custom-policy",
            role=self.lambda_role.name,
            policy_arn=lambda_policy.arn,
            opts=self.resource_options
        )

        # ✅ 4. DynamoDB Table for Storing Classification Results
        self.dynamodb_table = aws.dynamodb.Table(
            f"{self.prefix}-classification-results",
            attributes=[
                {"name": "ImageKey", "type": "S"}
            ],
            billing_mode="PAY_PER_REQUEST",
            hash_key="ImageKey",
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 5. SNS Topic for Manual Review Alerts
        self.sns_topic = aws.sns.Topic(f"{self.prefix}-manual-review-alerts", 
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 6. API Handler Lambda
        self.api_lambda = aws.lambda_.Function(f"{self.prefix}-api-handler",
            runtime="python3.9",
            handler="api_handler.lambda_handler",
            role=self.lambda_role.arn,
            memory_size=512,
            timeout=30, # Increased timeout for processing uploads
            code=pulumi.FileArchive("api_handler.zip"),
            environment={
                "variables": {
                    "BUCKET_NAME": self.image_bucket.id,
                    "DYNAMODB_TABLE": self.dynamodb_table.name,
                    "SNS_TOPIC_ARN": self.sns_topic.arn,
                    "TABLE_NAME": self.dynamodb_table.name
                }
            },
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 7. Image Processor Lambda
        self.image_lambda = aws.lambda_.Function(f"{self.prefix}-image-processor",
            runtime="python3.9",
            handler="image_processor.lambda_handler",
            role=self.lambda_role.arn,
            memory_size=1024,
            timeout=15,
            code=pulumi.FileArchive("image_processor.zip"),
            environment={
                "variables": {
                    "BUCKET_NAME": self.image_bucket.id,
                    "DYNAMODB_TABLE": self.dynamodb_table.name,
                    "TABLE_NAME": self.dynamodb_table.name
                }
            },
            tags=self.tags,
            opts=self.resource_options
        )

        # Lambda permission for S3 invocation - moved up before S3 notification
        self.lambda_permission = aws.lambda_.Permission(f"{self.prefix}-s3-permission",
            action="lambda:InvokeFunction",
            function=self.image_lambda.name,
            principal="s3.amazonaws.com",
            source_arn=self.image_bucket.arn,
            opts=self.resource_options
        )

        # S3 Event Trigger for Image Processor Lambda - now after lambda_permission
        self.s3_notification = aws.s3.BucketNotification(f"{self.prefix}-upload-notification",
            bucket=self.image_bucket.id,
            lambda_functions=[{
                "lambda_function_arn": self.image_lambda.arn,
                "events": ["s3:ObjectCreated:*"],
                "filter_prefix": "uploads/"
            }],
            opts=pulumi.ResourceOptions.merge(
                self.resource_options,
                pulumi.ResourceOptions(depends_on=[self.lambda_permission])
            )
        )

        # ✅ 8. Training Handler Lambda
        self.training_lambda = aws.lambda_.Function(f"{self.prefix}-training-handler",
            runtime="python3.9",
            handler="training_handler.lambda_handler",
            role=self.lambda_role.arn,
            memory_size=1024,
            timeout=900,
            code=pulumi.FileArchive("training_handler.zip"),
            environment={
                "variables": {
                    "BUCKET_NAME": self.image_bucket.id,
                    "TRAINING_JOB_NAME": f"{self.prefix}-classifier",
                    "SAGEMAKER_ROLE_ARN": self.lambda_role.arn,
                    "TRAINING_IMAGE": "763104351884.dkr.ecr.ap-southeast-1.amazonaws.com/tensorflow-training:2.6.3-gpu-py38-cu112-ubuntu20.04",
                    "TRAINING_DATA_S3_PATH": pulumi.Output.concat("s3://", self.image_bucket.id, "/training-data"),
                    "OUTPUT_S3_PATH": pulumi.Output.concat("s3://", self.image_bucket.id, "/training-output")
                }
            },
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 9. API Gateway for Lambda Invocation
        self.api_gateway = aws.apigatewayv2.Api(f"{self.prefix}-api",
            protocol_type="HTTP",
            cors_configuration={
                "allow_origins": ["*"],
                "allow_methods": ["POST", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key", "X-Amz-Security-Token"]
            },
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 10. API Integration with Lambda
        self.lambda_integration = aws.apigatewayv2.Integration(f"{self.prefix}-lambda-integration",
            api_id=self.api_gateway.id,
            integration_type="AWS_PROXY",
            integration_uri=self.api_lambda.invoke_arn,
            integration_method="POST",
            payload_format_version="2.0",
            opts=self.resource_options
        )

        # ✅ 11. API Route (POST /classify)
        self.route = aws.apigatewayv2.Route(f"{self.prefix}-api-route",
            api_id=self.api_gateway.id,
            route_key="POST /classify",
            target=pulumi.Output.concat("integrations/", self.lambda_integration.id),
            opts=self.resource_options
        )

        # Lambda permission for API Gateway invocation
        self.api_permission = aws.lambda_.Permission(f"{self.prefix}-api-gateway-permission",
            action="lambda:InvokeFunction",
            function=self.api_lambda.name,
            principal="apigateway.amazonaws.com",
            source_arn=pulumi.Output.concat(self.api_gateway.execution_arn, "/*/*"),
            opts=self.resource_options
        )

        # ✅ 12. Deploy API Gateway
        self.deployment = aws.apigatewayv2.Deployment(f"{self.prefix}-deployment",
            api_id=self.api_gateway.id,
            # Explicitly depend on the route
            opts=pulumi.ResourceOptions.merge(
                self.resource_options,
                pulumi.ResourceOptions(depends_on=[self.route, self.api_permission])
            )   
        )

        self.stage = aws.apigatewayv2.Stage(f"{self.prefix}-stage",
            api_id=self.api_gateway.id,
            name="dev",
            auto_deploy=True, # Enable auto-deploy for easier updates
            deployment_id=self.deployment.id,
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 13. Frontend Hosting S3 Bucket (private)
        self.frontend_bucket = aws.s3.Bucket(f"{self.prefix}-frontend-bucket",
            # Website configuration still needed for proper index.html handling
            website={
                "index_document": "index.html",
                "error_document": "index.html"
            },
            # Keep bucket private
            tags=self.tags,
            opts=self.resource_options
        )

        # Set bucket ownership controls
        aws.s3.BucketOwnershipControls(f"{self.prefix}-frontend-bucket-ownership",
            bucket=self.frontend_bucket.id,
            rule={
                "object_ownership": "BucketOwnerPreferred"
            },
            opts=self.resource_options
        )

        # ✅ 14. CloudFront Distribution for Frontend
        # Create an Origin Access Identity for CloudFront
        self.cloudfront_origin_access_identity = aws.cloudfront.OriginAccessIdentity(
            f"{self.prefix}-cloudfront-oai",
            comment=f"OAI for {self.prefix} frontend bucket",
            opts=self.resource_options
        )

        # Create a bucket policy that allows CloudFront OAI to access the bucket
        # This is a secure alternative to making the bucket public
        self.frontend_bucket_policy = aws.s3.BucketPolicy(
            f"{self.prefix}-frontend-bucket-policy",
            bucket=self.frontend_bucket.id,
            policy=pulumi.Output.all(
                bucket_name=self.frontend_bucket.id,
                cloudfront_oai=self.cloudfront_origin_access_identity.iam_arn
            ).apply(lambda args: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": args["cloudfront_oai"]
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{args['bucket_name']}/*"
                }]
            })),
            opts=self.resource_options
        )

        # Create the CloudFront distribution
        self.cloudfront_distribution = aws.cloudfront.Distribution(
            f"{self.prefix}-cloudfront",
            enabled=True,
            # Default root object (index.html)
            default_root_object="index.html",
            # Origins configuration (S3 bucket)
            origins=[{
                "origin_id": "S3Origin",
                "domain_name": self.frontend_bucket.bucket_regional_domain_name,
                "s3_origin_config": {
                    "origin_access_identity": pulumi.Output.concat(
                        "origin-access-identity/cloudfront/", 
                        self.cloudfront_origin_access_identity.id
                    )
                }
            }],
            # Default cache behavior
            default_cache_behavior={
                "target_origin_id": "S3Origin",
                "viewer_protocol_policy": "redirect-to-https",
                "allowed_methods": ["GET", "HEAD", "OPTIONS"],
                "cached_methods": ["GET", "HEAD"],
                "forwarded_values": {
                    "query_string": False,
                    "cookies": {
                        "forward": "none"
                    }
                },
                "min_ttl": 0,
                "default_ttl": 3600,
                "max_ttl": 86400,
                "compress": True
            },
            # Price class (use only North America and Europe for cost savings)
            price_class="PriceClass_100",
            # No restriction on who can access the content
            restrictions={
                "geo_restriction": {
                    "restriction_type": "none"
                }
            },
            # Default CloudFront certificate
            viewer_certificate={
                "cloudfront_default_certificate": True
            },
            # Custom error responses for SPA routing
            custom_error_responses=[
                {
                    "error_code": 403,
                    "response_code": 200,
                    "response_page_path": "/index.html"
                },
                {
                    "error_code": 404,
                    "response_code": 200,
                    "response_page_path": "/index.html"
                }
            ],
            tags=self.tags,
            opts=self.resource_options
        )

        # ✅ 15. Export all important outputs
        pulumi.export("api_endpoint", pulumi.Output.concat(self.stage.invoke_url, "/classify"))
        pulumi.export("frontend_url", pulumi.Output.concat("https://", self.cloudfront_distribution.domain_name))
        pulumi.export("image_bucket_name", self.image_bucket.id)
        pulumi.export("frontend_bucket_name", self.frontend_bucket.id)
        pulumi.export("dynamodb_table_name", self.dynamodb_table.name)