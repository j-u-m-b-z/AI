# API Documentation

## Endpoints

### 1. Image Classification

**POST /classify**  
Uploads an image and classifies it using both SageMaker and Rekognition.

### 2. Query Classification Results

**GET /results/{image_id}**  
Retrieves classification results for a given image.

## Deployment Steps

1. Install dependencies: `pip install -r requirements.txt`
2. Deploy AWS CDK stack: `cdk deploy`
3. Upload an image via CLI: `python client/cli.py --upload test.jpg`
4. Query classification results: `python client/cli.py --query test-image-id`
