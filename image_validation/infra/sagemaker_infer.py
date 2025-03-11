import os
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sagemaker_runtime = boto3.client('sagemaker-runtime')
SAGEMAKER_ENDPOINT = os.environ.get('SAGEMAKER_ENDPOINT')

def classify_with_sagemaker(bucket_name, image_key):
    try:
        s3 = boto3.client('s3')
        image_obj = s3.get_object(Bucket=bucket_name, Key=image_key)
        image_bytes = image_obj['Body'].read()

        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_ENDPOINT,
            ContentType='application/x-image',
            Body=image_bytes
        )

        result = json.loads(response['Body'].read().decode())
        predictions = result.get("predictions", [])

        for prediction in predictions:
            if prediction.get("class") == "person" and prediction.get("confidence", 0) >= 0.7:
                return "human"
        
        return "not_human"

    except Exception as e:
        logger.error(f"Error in SageMaker classification: {str(e)}")
        return "error"
