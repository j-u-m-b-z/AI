import pulumi
import pulumi_aws as aws
import json

class HumanImageValidationStack:
    def __init__(self):
        # ✅ S3 Bucket for image storage
        self.image_bucket = aws.s3.Bucket("human-image-validation-bucket")

        # ✅ IAM Role for Lambda
        lambda_role = aws.iam.Role("lambdaRole",
            assume_role_policy=json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Action": "sts:AssumeRole",
                    "Effect": "Allow",
                    "Principal": { "Service": "lambda.amazonaws.com" }
                }]
            })
        )

        # ✅ Attach policies to Lambda role
        aws.iam.RolePolicyAttachment("lambda-basic-exec",
            role=lambda_role.name,
            policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )

        # ✅ API Handler Lambda
        self.api_lambda = aws.lambda_.Function("apiHandler",
            runtime="python3.9",
            handler="api_handler.lambda_handler",
            role=lambda_role.arn,
            code=pulumi.FileArchive("api_handler.zip"),
            environment={"variables": {"BUCKET_NAME": self.image_bucket.id}}
        )

        # ✅ Image Processor Lambda
        self.image_lambda = aws.lambda_.Function("imageProcessor",
            runtime="python3.9",
            handler="image_processor.lambda_handler",
            role=lambda_role.arn,
            code=pulumi.FileArchive("image_processor.zip"),
            environment={"variables": {"BUCKET_NAME": self.image_bucket.id}}
        )

        # ✅ Training Handler Lambda
        self.training_lambda = aws.lambda_.Function("trainingHandler",
            runtime="python3.9",
            handler="training_handler.lambda_handler",
            role=lambda_role.arn,
            code=pulumi.FileArchive("training_handler.zip"),
            environment={"variables": {"BUCKET_NAME": self.image_bucket.id}}
        )

        # ✅ API Gateway
        self.api_gateway = aws.apigatewayv2.Api("humanCheckApi",
            protocol_type="HTTP"
        )

        # ✅ API Integration with Lambda
        lambda_integration = aws.apigatewayv2.Integration("lambdaIntegration",
            api_id=self.api_gateway.id,
            integration_type="AWS_PROXY",
            integration_uri=self.api_lambda.invoke_arn
        )

        # ✅ API Route
        aws.apigatewayv2.Route("route",
            api_id=self.api_gateway.id,
            route_key="POST /classify",
            target=lambda_integration.id
        )

        # ✅ Deploy API Gateway
        deployment = aws.apigatewayv2.Deployment("deployment",
            api_id=self.api_gateway.id
        )

        self.stage = aws.apigatewayv2.Stage("stage",
            api_id=self.api_gateway.id,
            name="dev",
            deployment_id=deployment.id
        )

        # ✅ Frontend Hosting S3 Bucket
        self.frontend_bucket = aws.s3.Bucket("livecheck-ui-bucket",
            website={
                "index_document": "index.html"
            }
        )
