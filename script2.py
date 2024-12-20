import os
import logging
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from botocore.exceptions import BotoCoreError, ClientError
from eks_token import get_token  # Importing the eks-token library for token generation
import base64

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "us-east-1"

def get_eks_token(cluster_name):
    """Retrieve the token for authenticating with an EKS cluster."""
    try:
        # Generate token using eks-token library
        auth_token = get_token(cluster_name=cluster_name, region=REGION)

        # Get EKS cluster details
        eks_client = boto3.client("eks", region_name=REGION)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        
        cluster_endpoint = cluster_info["cluster"]["endpoint"]
        cluster_cert = cluster_info["cluster"]["certificateAuthority"]["data"]

        return auth_token, cluster_endpoint, cluster_cert
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Error retrieving EKS token: {str(e)}")
        raise

def configure_k8s_client(cluster_name):
    """Configure Kubernetes client to interact with EKS cluster."""
    try:
        token, cluster_endpoint, cluster_cert = get_eks_token(cluster_name)

        configuration = client.Configuration()
        configuration.host = cluster_endpoint
        configuration.verify_ssl = True
        configuration.ssl_ca_cert = "/tmp/eks-ca.crt"
        configuration.api_key["authorization"] = f"Bearer {token}"

        with open(configuration.ssl_ca_cert, "w") as cert_file:
            cert_file.write(base64.b64decode(cluster_cert).decode("utf-8"))
        
        client.Configuration.set_default(configuration)
        logger.info("Kubernetes client successfully configured.")
    except Exception as e:
        logger.error(f"Error configuring Kubernetes client: {str(e)}")
        raise

def delete_pod(namespace, pod_name):
    """Delete a specific pod in the given namespace."""
    try:
        v1 = client.CoreV1Api()
        logger.info(f"Deleting pod {pod_name} in namespace {namespace}...")
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Deleted pod {pod_name} successfully.")
    except ApiException as e:
        if e.status == 401:
            logger.error("Unauthorized access. Check RBAC or token generation.")
        else:
            logger.error(f"Error deleting pod {pod_name} in namespace {namespace}: {e}")
        raise

def lambda_handler(event, context):
    """Main Lambda handler function."""
    try:
        cluster_name = os.getenv("EKS_CLUSTER_NAME")
        if not cluster_name:
            raise ValueError("EKS_CLUSTER_NAME environment variable is not set.")

        # Configure Kubernetes client
        configure_k8s_client(cluster_name)

        # Fetch pod details from the event
        pods_to_delete = event.get("pods", [])

        if not pods_to_delete:
            logger.warning("No pods specified in the event payload. Exiting.")
            return {"status": "success", "message": "No pods to delete."}

        for pod in pods_to_delete:
            namespace = pod.get("namespace")
            pod_name = pod.get("name")

            if not namespace or not pod_name:
                logger.warning("Namespace or pod name is missing in the event. Skipping.")
                continue

            delete_pod(namespace, pod_name)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Lambda function failed: {e}")
        return {"status": "error", "message": str(e)}
