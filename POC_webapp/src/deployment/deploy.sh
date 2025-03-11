#!/bin/bash

# Deployment Script for POC Webapp

# Exit on any error
set -e

# Project Configuration
PROJECT_NAME="poc-webapp"
ENVIRONMENT="production"

# Change to the deployment directory
cd "$(dirname "$0")"

# 1. Install Dependencies
echo "Installing dependencies..."
npm install

# 2. Build Angular Application (from app directory)
echo "Building Angular Application..."
cd ../app
ng build --configuration=production
cd ../deployment

# 3. Prepare Pulumi Deployment
echo "Preparing Pulumi Deployment..."
pulumi config set project-name ${PROJECT_NAME}
pulumi config set environment ${ENVIRONMENT}

# 4. Preview Pulumi Deployment
echo "Previewing Infrastructure Deployment..."
pulumi preview

# 5. Deploy with Pulumi
echo "Deploying Infrastructure..."
pulumi up --yes

# 6. Get Deployment Outputs
WEBSITE_URL=$(pulumi stack output websiteUrl)
CDN_DOMAIN=$(pulumi stack output cdnDomain)

echo "🚀 Deployment Complete!"
echo "Website URL: $WEBSITE_URL"
echo "CDN Domain: $CDN_DOMAIN"