import boto3
import os
import json
import logging
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import yaml
import subprocess

# Load environment variables
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
EKS_CLUSTER_NAME = os.getenv("EKS_CLUSTER_NAME")
ALLOWED_NAMESPACES = ["ui", "dev"]

# Configure logging
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

def update_kubeconfig_with_iam_auth(cluster_name, region):
    """
    Update kubeconfig using aws-iam-authenticator, similar to JS script logic.
    """
    try:
        logger.info(f"Updating kubeconfig for cluster {cluster_name} in region {region}")
        
        # Create kubeconfig using aws-iam-authenticator
        kubeconfig = {
            "clusters": [
                {
                    "name": cluster_name,
                    "cluster": {
                        "server": get_cluster_endpoint(cluster_name, region),
                        "certificate-authority-data": get_ca_data(cluster_name, region)
                    }
                }
            ],
            "users": [
                {
                    "name": "lambda-user",
                    "user": {
                        "exec": {
                            "apiVersion": "client.authentication.k8s.io/v1beta1",
                            "command": "aws-iam-authenticator",
                            "args": ["token", "-i", cluster_name],
                            "env": [{"name": "AWS_REGION", "value": region}]
                        }
                    }
                }
            ],
            "contexts": [
                {
                    "name": "lambda-context",
                    "context": {
                        "cluster": cluster_name,
                        "user": "lambda-user"
                    }
                }
            ],
            "current-context": "lambda-context"
        }

        kubeconfig_path = "/tmp/kubeconfig.yaml"
        with open(kubeconfig_path, "w") as f:
            yaml.dump(kubeconfig, f)
        
        config.load_kube_config(config_file=kubeconfig_path)
        logger.info("Successfully updated kubeconfig using aws-iam-authenticator.")
    except Exception as e:
        logger.error(f"Failed to update kubeconfig: {str(e)}")
        raise

def get_cluster_endpoint(cluster_name, region):
    """Fetch the EKS cluster endpoint."""
    eks_client = boto3.client("eks", region_name=region)
    response = eks_client.describe_cluster(name=cluster_name)
    return response['cluster']['endpoint']

def get_ca_data(cluster_name, region):
    """Fetch the EKS cluster CA data."""
    eks_client = boto3.client("eks", region_name=region)
    response = eks_client.describe_cluster(name=cluster_name)
    return response['cluster']['certificateAuthority']['data']

def recycle_pod(namespace, pod_name):
    """Delete the specified pod in the namespace."""
    v1 = client.CoreV1Api()
    try:
        response = v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Successfully recycled pod {pod_name} in namespace {namespace}.")
        return f"Pod {pod_name} successfully recycled in namespace '{namespace}'."
    except ApiException as e:
        logger.error(f"Kubernetes API Exception: {str(e)}")
        raise

def lambda_handler(event, context):
    """Lambda function handler."""
    logger.info("Lambda Handler Triggered")
    if DEBUG:
        logger.debug(f"Event: {json.dumps(event, indent=2)}")

    namespace = event.get("namespace")
    pod_name = event.get("podName")

    # Input validation
    if not namespace or namespace not in ALLOWED_NAMESPACES:
        error_message = f"Error: Unauthorized namespace '{namespace}'. Allowed namespaces: {ALLOWED_NAMESPACES}"
        logger.error(error_message)
        return {"statusCode": 400, "body": error_message}
    if not pod_name:
        error_message = "Error: 'podName' parameter is required."
        logger.error(error_message)
        return {"statusCode": 400, "body": error_message}

    try:
        # Update kubeconfig using aws-iam-authenticator
        region = boto3.session.Session().region_name  # Automatically fetch region
        update_kubeconfig_with_iam_auth(EKS_CLUSTER_NAME, region)

        # Recycle the pod
        result = recycle_pod(namespace, pod_name)
        return {"statusCode": 200, "body": result}
    except Exception as e:
        logger.error(f"Error occurred: {str(e)}")
        return {"statusCode": 500, "body": str(e)}
