import boto3
import kubernetes
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import json
import logging

# Load environment variables
REGION = os.getenv("AWS_REGION")
DEBUG = os.getenv("DEBUG") == "true"
EKS_CLUSTER_NAME = os.getenv("EKS_CLUSTER_NAME")

# Hardcoded allowed namespaces for testing
ALLOWED_NAMESPACES = ["ui", "dev"]

# Configure logging
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

def update_kube_config(cluster_name, region):
    """Update kubeconfig for the specified cluster."""
    eks_client = boto3.client("eks", region_name=region)
    try:
        response = eks_client.describe_cluster(name=cluster_name)
        cluster = response["cluster"]

        # Create kubeconfig
        k8s_config = {
            "clusters": [
                {
                    "name": cluster_name,
                    "cluster": {
                        "server": cluster["endpoint"],
                        "certificate-authority-data": cluster["certificateAuthority"]["data"],
                    },
                }
            ],
            "users": [
                {
                    "name": "eks-user",
                    "user": {
                        "exec": {
                            "apiVersion": "client.authentication.k8s.io/v1beta1",
                            "command": "aws",
                            "args": ["eks", "get-token", "--cluster-name", cluster_name],
                            "env": [{"name": "AWS_REGION", "value": region}],
                        },
                    },
                }
            ],
            "contexts": [
                {
                    "name": "eks-context",
                    "context": {
                        "cluster": cluster_name,
                        "user": "eks-user",
                    },
                }
            ],
            "current-context": "eks-context",
        }

        kubeconfig_path = "/tmp/kubeconfig.yaml"
        with open(kubeconfig_path, "w") as f:
            import yaml
            yaml.dump(k8s_config, f)

        config.load_kube_config(config_file=kubeconfig_path)
        logger.info(f"Kubeconfig updated for cluster: {cluster_name}")
    except Exception as e:
        logger.error(f"Failed to update kubeconfig: {str(e)}")
        raise

def recycle_pod(namespace, pod_name):
    """Delete the specified pod in the namespace."""
    v1 = client.CoreV1Api()
    try:
        response = v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Pod {pod_name} recycled in namespace {namespace}: {response.status}")
        return f"Pod {pod_name} recycled in namespace {namespace}."
    except ApiException as e:
        logger.error(f"Kubernetes API Exception: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to recycle pod: {str(e)}")
        raise

def lambda_handler(event, context):
    """Lambda function handler for recycling Kubernetes pods."""
    logger.info("Recycle Pod Triggered")
    if DEBUG:
        logger.debug(f"Event: {json.dumps(event, indent=2)}")

    namespace = event.get("namespace")
    pod_name = event.get("podName")

    # Input validation
    if not namespace or namespace not in ALLOWED_NAMESPACES:
        error_message = f"Error: Invalid or unauthorized namespace '{namespace}'. Allowed namespaces: {ALLOWED_NAMESPACES}"
        logger.error(error_message)
        return {"statusCode": 400, "body": error_message}

    if not pod_name:
        error_message = "Error: 'podName' parameter is required."
        logger.error(error_message)
        return {"statusCode": 400, "body": error_message}

    try:
        # Update kubeconfig
        update_kube_config(EKS_CLUSTER_NAME, REGION)

        # Recycle the pod
        result = recycle_pod(namespace, pod_name)
        return {"statusCode": 200, "body": result}
    except Exception as e:
        error_message = f"Error occurred: {str(e)}"
        logger.error(error_message)
        return {"statusCode": 500, "body": error_message}
