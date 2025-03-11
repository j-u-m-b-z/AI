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
