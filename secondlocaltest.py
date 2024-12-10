import boto3
import subprocess
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import json
import logging

# Load environment variables
REGION = os.getenv("AWS_REGION", "us-east-1")
CLUSTER_MAPPING = json.loads(os.getenv("CLUSTER_MAPPING", "{}"))
ALLOWED_NAMESPACES = json.loads(os.getenv("ALLOWED_NAMESPACES", "[]"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def update_kubeconfig(cluster_name, region):
    """
    Update kubeconfig for the specified cluster.
    """
    try:
        command = ["aws", "eks", "update-kubeconfig", "--region", region, "--name", cluster_name]
        subprocess.run(command, check=True)
        logger.info(f"Kubeconfig updated for cluster: {cluster_name}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to update kubeconfig: {str(e)}")
        raise Exception(f"Failed to update kubeconfig: {str(e)}")

def recycle_pod(namespace, pod_name):
    """
    Delete the specified pod in the namespace.
    """
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return f"Pod {pod_name} recycled in namespace {namespace}."
    except ApiException as e:
        logger.error(f"Kubernetes API Exception: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to recycle pod: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda function handler to recycle a Kubernetes pod.
    """
    cluster_id = event.get("clusterId")
    namespace = event.get("namespace")
    pod_name = event.get("podName")

    # Validate input parameters
    if not cluster_id:
        return {"statusCode": 400, "body": "Error: 'clusterId' parameter is required."}
    if not namespace:
        return {"statusCode": 400, "body": "Error: 'namespace' parameter is required."}
    if not pod_name:
        return {"statusCode": 400, "body": "Error: 'podName' parameter is required."}

    # Check if namespace is allowed
    if namespace not in ALLOWED_NAMESPACES:
        return {
            "statusCode": 400,
            "body": f"Error: Namespace '{namespace}' is not allowed. Allowed namespaces: {', '.join(ALLOWED_NAMESPACES)}"
        }

    # Map cluster ID to cluster name
    cluster_name = CLUSTER_MAPPING.get(cluster_id)
    if not cluster_name:
        return {"statusCode": 400, "body": f"Error: Unknown clusterId '{cluster_id}'."}

    try:
        # Update kubeconfig for the selected cluster
        update_kubeconfig(cluster_name, REGION)

        # Perform Kubernetes operations
        config.load_kube_config()  # Load updated kubeconfig
        result = recycle_pod(namespace, pod_name)

        return {"statusCode": 200, "body": result}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
