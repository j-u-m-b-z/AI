import os
import json
import boto3
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS SageMaker client
sagemaker = boto3.client('sagemaker')

# Get environment variables
TRAINING_JOB_NAME = os.environ.get('TRAINING_JOB_NAME', 'YOLOv5TrainingJob')
SAGEMAKER_ROLE_ARN = os.environ.get('SAGEMAKER_ROLE_ARN')
TRAINING_IMAGE = os.environ.get('TRAINING_IMAGE', 'your-sagemaker-training-image')
TRAINING_DATA_S3_PATH = os.environ.get('TRAINING_DATA_S3_PATH')
OUTPUT_S3_PATH = os.environ.get('OUTPUT_S3_PATH')

def lambda_handler(event, context):
    """Trigger a SageMaker training job"""
    try:
        training_params = {
            "TrainingJobName": TRAINING_JOB_NAME,
            "AlgorithmSpecification": {
                "TrainingImage": TRAINING_IMAGE,
                "TrainingInputMode": "File"
            },
            "RoleArn": SAGEMAKER_ROLE_ARN,
            "InputDataConfig": [{
                "ChannelName": "training",
                "DataSource": {
                    "S3DataSource": {
                        "S3DataType": "S3Prefix",
                        "S3Uri": TRAINING_DATA_S3_PATH,
                        "S3DataDistributionType": "FullyReplicated"
                    }
                }
            }],
            "OutputDataConfig": {
                "S3OutputPath": OUTPUT_S3_PATH
            },
            "ResourceConfig": {
                "InstanceType": "ml.p3.2xlarge",
                "InstanceCount": 1,
                "VolumeSizeInGB": 50
            },
            "StoppingCondition": {
                "MaxRuntimeInSeconds": 86400
            }
        }

        response = sagemaker.create_training_job(**training_params)
        logger.info(f"Training job {TRAINING_JOB_NAME} started successfully.")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Training job started", "TrainingJobName": TRAINING_JOB_NAME})
        }

    except Exception as e:
        logger.error(f"Error starting training job: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }
