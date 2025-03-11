#!/bin/bash

# Make sure we're in the right directory
cd "/mnt/d/repos/AWS/AI projects/image_validation/infra"

echo "Creating API handler ZIP package..."
# Create directory structure
mkdir -p tmp_api_handler/utils

# Copy files to temporary directory (adjust paths if files are in different locations)
cp api_handler.py tmp_api_handler/
cp sagemaker_infer.py tmp_api_handler/ || echo "Warning: sagemaker_infer.py not found, creating placeholder"
cp rekognition_infer.py tmp_api_handler/ || echo "Warning: rekognition_infer.py not found, creating placeholder"

# If files don't exist, create placeholder versions
if [ ! -f "tmp_api_handler/sagemaker_infer.py" ]; then
  echo "Creating placeholder sagemaker_infer.py"
  cat > tmp_api_handler/sagemaker_infer.py << 'EOF'
import boto3
import json

def classify_with_sagemaker(bucket, key):
    """Classify image using SageMaker endpoint"""
    # Placeholder implementation
    return "Person"
EOF
fi

if [ ! -f "tmp_api_handler/rekognition_infer.py" ]; then
  echo "Creating placeholder rekognition_infer.py"
  cat > tmp_api_handler/rekognition_infer.py << 'EOF'
import boto3

def classify_with_rekognition(bucket, key):
    """Classify image using Amazon Rekognition"""
    client = boto3.client('rekognition')
    
    response = client.detect_labels(
        Image={
            'S3Object': {
                'Bucket': bucket,
                'Name': key
            }
        },
        MaxLabels=10,
        MinConfidence=70
    )
    
    # For simplicity, return the first label
    if response['Labels']:
        return response['Labels'][0]['Name']
    return "Unknown"
EOF
fi

# Make sure utils directory exists
mkdir -p tmp_api_handler/utils

# Create dynamodb_utils.py
cat > tmp_api_handler/utils/dynamodb_utils.py << 'EOF'
import boto3
import os

def save_classification_result(result):
    """Save classification result to DynamoDB"""
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ.get('TABLE_NAME'))
    
    item = {
        'ImageKey': result['image_id'],
        'SageMakerResult': result['sagemaker_result'],
        'RekognitionResult': result['rekognition_result'],
        'Agreement': result['agreement'],
        'Confidence': result['confidence']
    }
    
    if 'is_human' in result:
        item['IsHuman'] = result['is_human']
    
    table.put_item(Item=item)
    return True
EOF

# Create __init__.py
touch tmp_api_handler/utils/__init__.py

# Create ZIP file with absolute path
cd tmp_api_handler
zip -r "/mnt/d/repos/AWS/AI projects/image_validation/infra/api_handler.zip" .
cd ..

echo "Creating image processor ZIP package..."
# Create directory structure
mkdir -p tmp_image_processor/utils

# Copy files to temporary directory
cp api_handler.py tmp_image_processor/image_processor.py || echo "Warning: api_handler.py not found, creating placeholder"

# If file doesn't exist, create a placeholder version
if [ ! -f "tmp_image_processor/image_processor.py" ]; then
  echo "Creating placeholder image_processor.py"
  cat > tmp_image_processor/image_processor.py << 'EOF'
import os
import json
import boto3
from sagemaker_infer import classify_with_sagemaker
from rekognition_infer import classify_with_rekognition
from utils.dynamodb_utils import save_classification_result

TABLE_NAME = os.environ['TABLE_NAME']

def lambda_handler(event, context):
    s3_event = event['Records'][0]['s3']
    bucket_name = s3_event['bucket']['name']
    image_key = s3_event['object']['key']

    sagemaker_result = classify_with_sagemaker(bucket_name, image_key)
    rekognition_result = classify_with_rekognition(bucket_name, image_key)

    agreement = (sagemaker_result == rekognition_result)
    confidence = 0.5

    result = {
        "image_id": image_key,
        "sagemaker_result": sagemaker_result,
        "rekognition_result": rekognition_result,
        "agreement": agreement,
        "confidence": confidence
    }

    save_classification_result(result)
    return {"statusCode": 200, "body": json.dumps(result)}
EOF
fi

# Copy other files
cp tmp_api_handler/sagemaker_infer.py tmp_image_processor/
cp tmp_api_handler/rekognition_infer.py tmp_image_processor/
cp -r tmp_api_handler/utils tmp_image_processor/

# Create ZIP file with absolute path
cd tmp_image_processor
zip -r "/mnt/d/repos/AWS/AI projects/image_validation/infra/image_processor.zip" .
cd ..

echo "Creating training handler ZIP package..."
# Create directory structure
mkdir -p tmp_training_handler

# Create training_handler.py
cat > tmp_training_handler/training_handler.py << 'EOF'
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
EOF

# Create ZIP file with absolute path
cd tmp_training_handler
zip -r "/mnt/d/repos/AWS/AI projects/image_validation/infra/training_handler.zip" .
cd ..

# Verify that files exist and display their sizes
echo "Verifying created ZIP files:"
ls -la "/mnt/d/repos/AWS/AI projects/image_validation/infra/"*.zip

# Clean up temporary directories
rm -rf tmp_api_handler
rm -rf tmp_image_processor
rm -rf tmp_training_handler

echo "All Lambda packages created successfully"