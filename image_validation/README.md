# Two-Tier Image Classification System

## Overview
This project implements an automated, scalable, and highly accurate image classification system using AWS services.

## Features
- Uses SageMaker and Rekognition for two-tier validation
- API Gateway for easy access to classification results
- Stores classification results in DynamoDB

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Deploy AWS CDK: `cdk deploy`
3. Use `client/cli.py` for uploading images and retrieving results.
