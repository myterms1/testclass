import os
import logging
import subprocess
import json
from kubernetes import client
from kubernetes.client.rest import ApiException

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_eks_token(cluster_name):
    """
    Retrieve the token for authenticating with an EKS cluster using AWS CLI.
    """
    try:
        logger.info(f"Generating token for cluster: {cluster_name}")
        cmd = [
            "aws", "eks", "get-token",
            "--cluster-name", cluster_name,
            "--region", "us-east-1"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        token_output = json.loads(result.stdout)
        return token_output["status"]["token"]
    except subprocess.CalledProcessError as e:
        logger.error(f"Error generating EKS token: {e.stderr}")
        raise

def configure_k8s_client(cluster_name):
    """
    Configure Kubernetes client to interact with the EKS cluster.
    """
    try:
        token = get_eks_token(cluster_name)
        logger.info("Token successfully retrieved for Kubernetes client configuration.")

        # Configure the Kubernetes client
        configuration = client.Configuration()
        configuration.host = os.getenv("K8S_API_ENDPOINT")  # Set this to your cluster endpoint
        configuration.verify_ssl = True
        configuration.api_key["authorization"] = f"Bearer {token}"
        
        # Set the default configuration
        client.Configuration.set_default(configuration)
    except Exception as e:
        logger.error(f"Error configuring Kubernetes client: {str(e)}")
        raise

def delete_pod(namespace, pod_name):
    """
    Delete a specific pod in the given namespace.
    """
    try:
        v1 = client.CoreV1Api()
        logger.info(f"Attempting to delete pod: {pod_name} in namespace: {namespace}")
        response = v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Successfully deleted pod: {pod_name}. Response: {response}")
    except ApiException as e:
        logger.error(f"Error deleting pod {pod_name} in namespace {namespace}: {e}")
        raise

def lambda_handler(event, context):
    """
    Lambda handler function to process events and delete specified pods.
    """
    try:
        cluster_name = os.getenv("EKS_CLUSTER_NAME")
        if not cluster_name:
            raise ValueError("EKS_CLUSTER_NAME environment variable is not set.")

        # Configure Kubernetes client
        configure_k8s_client(cluster_name)

        # Fetch pod details from the event
        pods_to_delete = event.get("pods", [])
        if not pods_to_delete:
            raise ValueError("No pods specified in the event for deletion.")

        for pod in pods_to_delete:
            namespace = pod.get("namespace")
            pod_name = pod.get("name")
            if not namespace or not pod_name:
                logger.warning(f"Invalid pod details: {pod}. Skipping.")
                continue

            delete_pod(namespace, pod_name)

        return {"status": "success", "message": "All specified pods deleted successfully."}
    except Exception as e:
        logger.error(f"Lambda function encountered an error: {str(e)}")
        return {"status": "error", "message": str(e)}
