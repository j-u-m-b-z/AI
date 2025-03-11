import os
import json
import boto3
import logging
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ.get('TABLE_NAME')
table = dynamodb.Table(TABLE_NAME)

def save_classification_result(result):
    try:
        result['timestamp'] = datetime.utcnow().isoformat()

        table.put_item(Item=result)
        logger.info(f"Successfully saved result for image: {result['image_id']}")
        return True

    except Exception as e:
        logger.error(f"Error saving result to DynamoDB: {str(e)}")
        return False
