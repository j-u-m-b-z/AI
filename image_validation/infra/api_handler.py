import os
import json
import boto3
import base64
import logging
import cgi
import io

from sagemaker_infer import classify_with_sagemaker
from rekognition_infer import classify_with_rekognition
from utils.dynamodb_utils import save_classification_result

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment Variables
TABLE_NAME = os.environ.get('TABLE_NAME')
BUCKET_NAME = os.environ.get('BUCKET_NAME', '')

# Initialize AWS Clients
s3 = boto3.client('s3')

def lambda_handler(event, context):
    """Determine whether request is from API Gateway or S3 Event and process accordingly."""
    try:
        # API Gateway Event
        if event.get('httpMethod') or event.get('requestContext'):
            return handle_api_request(event, context)
        
        # S3 Event
        elif 'Records' in event and 's3' in event['Records'][0]:
            return handle_s3_event(event, context)
        
        # Unknown Event
        else:
            logger.error("Invalid event structure received")
            return format_response({'error': 'Invalid event structure'}, 400)

    except Exception as e:
        logger.error(f"Unhandled error in Lambda: {str(e)}")
        return format_response({'error': 'Internal server error'}, 500)

# --------------------------------------
# ✅ API Gateway Handler (Direct Upload)
# --------------------------------------
def handle_api_request(event, context):
    """Handles image upload via API Gateway and classifies using SageMaker & Rekognition."""
    if event.get('httpMethod') == 'OPTIONS':
        return format_response('', 200, cors=True)

    try:
        # Extract request body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(body)

        # Parse multipart/form-data request
        headers = event.get('headers', {})
        environ = {'REQUEST_METHOD': 'POST'}
        if headers and 'content-type' in headers:
            environ['CONTENT_TYPE'] = headers['content-type']

        # Read image from request
        fp = io.BytesIO(body.encode('utf-8') if isinstance(body, str) else body)
        form = cgi.FieldStorage(fp=fp, environ=environ)

        if 'image' not in form:
            return format_response({'error': 'No image file provided'}, 400)

        fileitem = form['image']
        image_bytes = fileitem.file.read()

        # Generate unique S3 Key
        image_key = f"uploads/{context.aws_request_id}.jpg"

        # Upload to S3
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=image_key,
            Body=image_bytes,
            ContentType='image/jpeg'
        )
        logger.info(f"Uploaded image to S3: s3://{BUCKET_NAME}/{image_key}")

        # Process Image
        return classify_and_store_result(image_key)

    except Exception as e:
        logger.error(f"Error in API request processing: {str(e)}")
        return format_response({'error': 'Image processing failed'}, 500)

# --------------------------------------
# ✅ S3 Event Handler (Uploaded Image)
# --------------------------------------
def handle_s3_event(event, context):
    """Handles image classification when a new image is uploaded to S3."""
    try:
        # Extract S3 event data
        s3_event = event['Records'][0]['s3']
        image_key = s3_event['object']['key']

        # Process Image
        return classify_and_store_result(image_key)

    except Exception as e:
        logger.error(f"Error processing S3 event: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to process S3 event"})}

# --------------------------------------
# ✅ Image Classification & Result Storage
# --------------------------------------
def classify_and_store_result(image_key):
    """Runs SageMaker & Rekognition, compares results, and stores in DynamoDB."""
    try:
        # Run classifications
        sagemaker_result = classify_with_sagemaker(BUCKET_NAME, image_key)
        rekognition_result = classify_with_rekognition(BUCKET_NAME, image_key)

        # Determine agreement & confidence
        agreement = (sagemaker_result == rekognition_result)
        confidence = 0.85 if agreement else 0.5  # Example confidence metric
        is_human = (sagemaker_result == "human" or rekognition_result == "human")

        # Create result object
        result = {
            "image_id": image_key,
            "sagemaker_result": sagemaker_result,
            "rekognition_result": rekognition_result,
            "agreement": agreement,
            "confidence": confidence,
            "is_human": is_human
        }

        # Save to DynamoDB
        save_classification_result(result)

        # Return API Response
        return format_response({
            "is_human": is_human,
            "confidence": confidence,
            "details": {
                "sagemaker_result": sagemaker_result,
                "rekognition_result": rekognition_result,
                "agreement": agreement
            }
        })

    except Exception as e:
        logger.error(f"Classification process failed: {str(e)}")
        return format_response({'error': 'Classification failed'}, 500)

# --------------------------------------
# ✅ Response Formatter
# --------------------------------------
def format_response(body, status_code=200, cors=True):
    """Formats API response with optional CORS headers."""
    headers = {'Content-Type': 'application/json'}
    if cors:
        headers.update({
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        })
    
    return {
        'statusCode': status_code,
        'headers': headers,
        'body': json.dumps(body)
    }
