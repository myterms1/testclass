import os
import logging
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import base64
import subprocess
import json

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.getenv("AWS_REGION", "us-east-1")
CLUSTER_NAME = os.getenv("EKS_CLUSTER_NAME")
NAMESPACE = os.getenv("K8S_NAMESPACE")

def get_eks_cluster_info(cluster_name):
    """Retrieve EKS cluster endpoint and certificate authority data."""
    try:
        eks_client = boto3.client("eks", region_name=REGION)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        return {
            "endpoint": cluster_info["cluster"]["endpoint"],
            "ca_data": cluster_info["cluster"]["certificateAuthority"]["data"]
        }
    except Exception as e:
        logger.error(f"Error retrieving EKS cluster info: {e}")
        raise

def generate_token(cluster_name):
    """Generate a token using aws-iam-authenticator."""
    try:
        cmd = [
            "aws-iam-authenticator", "token", "-i", cluster_name
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        token_data = json.loads(result.stdout)
        return token_data["status"]["token"]
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating token: {e.stderr}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding token JSON: {e}")
        raise

def configure_k8s_client(cluster_name):
    """Set up Kubernetes client dynamically with token-based authentication."""
    cluster_info = get_eks_cluster_info(cluster_name)
    token = generate_token(cluster_name)

    configuration = client.Configuration()
    configuration.host = cluster_info["endpoint"]
    configuration.verify_ssl = True
    configuration.ssl_ca_cert = "/tmp/eks-ca.crt"
    configuration.api_key = {"authorization": f"Bearer {token}"}

    # Write the CA data to a temporary file
    with open(configuration.ssl_ca_cert, "w") as ca_file:
        ca_file.write(base64.b64decode(cluster_info["ca_data"]).decode("utf-8"))

    client.Configuration.set_default(configuration)

def delete_pod(namespace, pod_name):
    """Delete a specific pod in the given namespace."""
    try:
        v1 = client.CoreV1Api()
        logger.info(f"Deleting pod {pod_name} in namespace {namespace}...")
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Pod {pod_name} successfully deleted.")
    except ApiException as e:
        logger.error(f"Failed to delete pod {pod_name} in namespace {namespace}: {e}")
        raise

def lambda_handler(event, context):
    """Main Lambda handler."""
    try:
        if not CLUSTER_NAME or not NAMESPACE:
            raise ValueError("EKS_CLUSTER_NAME and K8S_NAMESPACE must be set as environment variables.")

        # Configure Kubernetes client
        configure_k8s_client(CLUSTER_NAME)

        # Parse event for pods to delete
        pods_to_delete = event.get("pods", [])
        if not pods_to_delete:
            raise ValueError("No pods specified in the event payload.")

        for pod in pods_to_delete:
            pod_name = pod.get("name")
            namespace = pod.get("namespace", NAMESPACE)
            if not pod_name:
                logger.warning("Pod name is missing in the payload. Skipping.")
                continue
            delete_pod(namespace, pod_name)

        return {"status": "success", "message": "Pods deleted successfully."}
    except Exception as e:
        logger.error(f"Error in Lambda function: {e}")
        return {"status": "error", "message": str(e)}
