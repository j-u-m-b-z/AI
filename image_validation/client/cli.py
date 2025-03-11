import argparse
import requests

BASE_URL = "https://your-api-gateway-url"

def upload_image(image_path):
    files = {'file': open(image_path, 'rb')}
    response = requests.post(f"{BASE_URL}/classify", files=files)
    print(response.json())

def query_result(image_id):
    response = requests.get(f"{BASE_URL}/results/{image_id}")
    print(response.json())

parser = argparse.ArgumentParser(description="CLI for Image Classification")
parser.add_argument("--upload", help="Path to image file")
parser.add_argument("--query", help="Image ID to query results")

args = parser.parse_args()
if args.upload:
    upload_image(args.upload)
elif args.query:
    query_result(args.query)
