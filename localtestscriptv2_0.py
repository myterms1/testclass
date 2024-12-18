import boto3
import os
import json
import logging
import sys
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Environment Variables
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
EKS_CLUSTER_NAME = os.getenv("EKS_CLUSTER_NAME", "gbs-dev-facets-eks-blue")
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
ALLOWED_NAMESPACES = ["ui", "dev"]

# Logging Configuration
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

def update_kubeconfig(cluster_name, region):
    """
    Update kubeconfig for the specified cluster.
    """
    logger.info("Updating kubeconfig for cluster: %s in region: %s", cluster_name, region)
    try:
        command = f"aws eks update-kubeconfig --region {region} --name {cluster_name}"
        os.system(command)
        logger.info("Successfully updated kubeconfig.")
    except Exception as e:
        logger.error("Failed to update kubeconfig: %s", e)
        raise

def recycle_pod(namespace, pod_name):
    """
    Delete the specified pod in the namespace.
    """
    try:
        v1 = client.CoreV1Api()
        logger.info("Attempting to delete pod: %s in namespace: %s", pod_name, namespace)
        response = v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info("Successfully deleted pod: %s", pod_name)
        return response.status
    except ApiException as e:
        logger.error("Kubernetes API Exception: %s", e)
        raise
    except Exception as e:
        logger.error("Error occurred while deleting pod: %s", e)
        raise

def lambda_handler(event, context):
    """
    Lambda function handler to recycle a Kubernetes pod.
    """
    logger.info("Lambda Handler Triggered")
    logger.debug("Event: %s", json.dumps(event, indent=2))

    # Extract input parameters
    namespace = event.get("namespace")
    pod_name = event.get("podName")

    # Input validation
    if not namespace or namespace not in ALLOWED_NAMESPACES:
        error_message = f"Error: Namespace '{namespace}' is invalid or not allowed. Allowed namespaces: {ALLOWED_NAMESPACES}"
        logger.error(error_message)
        return {"statusCode": 400, "body": error_message}

    if not pod_name:
        error_message = "Error: 'podName' parameter is required."
        logger.error(error_message)
        return {"statusCode": 400, "body": error_message}

    try:
        # Update kubeconfig
        update_kubeconfig(EKS_CLUSTER_NAME, AWS_REGION)

        # Load kubeconfig
        config.load_kube_config()
        logger.info("Loaded kubeconfig successfully.")

        # Recycle pod
        result = recycle_pod(namespace, pod_name)
        success_message = f"Successfully recycled pod '{pod_name}' in namespace '{namespace}'."
        logger.info(success_message)
        return {"statusCode": 200, "body": success_message}

    except Exception as e:
        error_message = f"Error occurred: {str(e)}"
        logger.error(error_message)
        return {"statusCode": 500, "body": error_message}

if __name__ == "__main__":
    """
    Simulate Lambda event input locally.
    Usage: python local_pod_recycler.py test_event.json
    """
    if len(sys.argv) != 2:
        print("Usage: python local_pod_recycler.py <test_event.json>")
        sys.exit(1)

    # Read input file
    input_file = sys.argv[1]
    with open(input_file, "r") as f:
        event = json.load(f)

    # Call the lambda_handler function
    response = lambda_handler(event, None)
    print("Response:", response)
