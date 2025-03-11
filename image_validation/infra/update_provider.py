#!/usr/bin/env python3
"""
Script to update all resources in stack.py to use the provided AWS provider
"""
import re

def add_opts_to_resource(match):
    """Add opts parameter to resource instantiation if it doesn't have one"""
    full_match = match.group(0)
    
    # If it already has an opts parameter, just return the original
    if "opts=" in full_match:
        return full_match
    
    # If it has trailing parameters, add opts before the closing parenthesis
    if full_match.strip().endswith(")"):
        return full_match[:-1] + ",\n            opts=resource_options)"
    else:
        # No trailing parenthesis yet, probably more parameters
        return full_match + ",\n            opts=resource_options"

def update_stack_file():
    """Update the stack.py file to pass resource_options to all resources"""
    # Read the stack.py file
    with open("stack.py", "r") as f:
        content = f.read()
    
    # Regular expression to find AWS resource instantiations
    # This pattern looks for lines like: self.resource_name = aws.service.Resource("name",
    pattern = r'(self\.\w+\s*=\s*aws\.\w+\.\w+\(\s*"\w+",)'
    
    # Replace all matches with versions that include opts parameter
    updated_content = re.sub(pattern, add_opts_to_resource, content)
    
    # Write back to the file
    with open("stack.py", "w") as f:
        f.write(updated_content)
    
    print("Updated stack.py with provider options for all resources")

if __name__ == "__main__":
    update_stack_file()