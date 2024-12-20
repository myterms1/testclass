import os
import subprocess
import json
import logging
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from botocore.exceptions import BotoCoreError, ClientError
import base64

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = "us-east-1"

def get_eks_token(cluster_name):
    """Retrieve the token for authenticating with an EKS cluster."""
    try:
        # Using AWS CLI to generate the token
        cmd = [
            "aws", "eks", "get-token",
            "--cluster-name", cluster_name,
            "--region", REGION
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        token_output = json.loads(result.stdout)
        token = token_output["status"]["token"]
        cluster_endpoint = token_output["status"]["clusterEndpoint"]
        cluster_cert = token_output["status"]["clusterCertificateAuthorityData"]

        return token, cluster_endpoint, cluster_cert
    except subprocess.CalledProcessError as e:
        logger.error(f"Error retrieving EKS token: {str(e)}")
        raise


def configure_k8s_client(cluster_name):
    """Configure Kubernetes client to interact with EKS cluster."""
    token, cluster_endpoint, cluster_cert = get_eks_token(cluster_name)

    configuration = client.Configuration()
    configuration.host = cluster_endpoint
    configuration.verify_ssl = True
    configuration.ssl_ca_cert = "/tmp/eks-ca.crt"
    configuration.api_key["authorization"] = f"Bearer {token}"

    # Write the certificate authority data to a file
    with open(configuration.ssl_ca_cert, "w") as cert_file:
        cert_file.write(base64.b64decode(cluster_cert).decode("utf-8"))
    
    client.Configuration.set_default(configuration)

def delete_pod(namespace, pod_name):
    """Delete a specific pod in the given namespace."""
    try:
        v1 = client.CoreV1Api()
        logger.info(f"Deleting pod {pod_name} in namespace {namespace}...")
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Deleted pod {pod_name} successfully.")
    except ApiException as e:
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
