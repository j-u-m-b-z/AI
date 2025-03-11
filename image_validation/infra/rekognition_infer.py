import os
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

rekognition = boto3.client('rekognition')

def classify_with_rekognition(bucket_name, image_key):
    try:
        response = rekognition.detect_labels(
            Image={"S3Object": {"Bucket": bucket_name, "Name": image_key}},
            MaxLabels=10,
            MinConfidence=70
        )

        for label in response['Labels']:
            if label['Name'] == "Person":
                return "human"
        
        return "not_human"

    except Exception as e:
        logger.error(f"Error in Rekognition classification: {str(e)}")
        return "error"
