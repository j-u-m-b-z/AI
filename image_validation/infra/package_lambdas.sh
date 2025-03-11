#!/bin/bash

# Create directory for utils module if it doesn't exist
mkdir -p utils

# Create the dynamodb_utils.py file if it doesn't exist
if [ ! -f utils/dynamodb_utils.py ]; then
  echo "Creating dynamodb_utils.py file..."
  cat > utils/dynamodb_utils.py << 'EOF'
import boto3
import os

def save_classification_result(result):
    """
    Save classification result to DynamoDB
    """
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ.get('DYNAMODB_TABLE'))
    
    item = {
        'ImageKey': result['image_id'],
        'SageMakerResult': result['sagemaker_result'],
        'RekognitionResult': result['rekognition_result'],
        'Agreement': result['agreement'],
        'Confidence': result['confidence']
    }
    
    table.put_item(Item=item)
    return True
EOF
fi

# Create rekognition_infer.py and sagemaker_infer.py if they don't exist
if [ ! -f rekognition_infer.py ]; then
  echo "Creating rekognition_infer.py file..."
  cat > rekognition_infer.py << 'EOF'
import boto3

def classify_with_rekognition(bucket, key):
    """
    Classify image using Amazon Rekognition
    """
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

if [ ! -f sagemaker_infer.py ]; then
  echo "Creating sagemaker_infer.py file..."
  cat > sagemaker_infer.py << 'EOF'
import boto3
import json

def classify_with_sagemaker(bucket, key):
    """
    Classify image using SageMaker endpoint
    """
    # This is a simplified version. In production, you'd:
    # 1. Download the image from S3
    # 2. Preprocess it 
    # 3. Send it to SageMaker endpoint
    # 4. Parse response
    
    # For demo purposes, we'll just return a placeholder
    return "Person"
EOF
fi

# Create __init__.py in utils directory
touch utils/__init__.py

# Package Lambda functions
echo "Packaging api_handler.py..."
zip -r api_handler.zip api_handler.py utils/ rekognition_infer.py sagemaker_infer.py

echo "Packaging image_processor.py..."
zip -r image_processor.zip image_processor.py utils/ rekognition_infer.py sagemaker_infer.py

echo "Packaging training_handler.py..."
zip -r training_handler.zip training_handler.py

echo "Lambda packaging complete!"