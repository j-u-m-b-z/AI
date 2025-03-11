"""Human Image Validation System - Pulumi Infrastructure"""

import pulumi
import pulumi_aws as aws

# Configure the AWS Provider to use ap-southeast-1 region
aws_provider = aws.Provider("aws-provider", region="ap-southeast-1")

# Import the stack with the specific provider
from stack import HumanImageValidationStack

# Initialize the Human Image Validation Stack with the provider
stack = HumanImageValidationStack(provider=aws_provider)