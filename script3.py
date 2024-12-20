import os
import logging
import boto3
from kubernetes import client
from kubernetes.client.rest import ApiException
from botocore.exceptions import BotoCoreError, ClientError
import base64

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION = os.getenv("AWS_REGION", "us-east-1")  # Default region if not set

def get_eks_token(cluster_name, region):
    """Retrieve the token for authenticating with an EKS cluster."""
    try:
        # Using AWS CLI to generate the token
        session = boto3.session.Session()
        eks_client = session.client("eks", region_name=region)
        cluster_info = eks_client.describe_cluster(name=cluster_name)

        cluster_endpoint = cluster_info["cluster"]["endpoint"]
        cluster_cert = cluster_info["cluster"]["certificateAuthority"]["data"]

        sts_client = session.client("sts", region_name=region)
        identity = sts_client.get_caller_identity()
        token = (
            "k8s-aws-v1."
            + base64.urlsafe_b64encode(f"{identity['Arn']}:{identity['Account']}".encode()).decode().rstrip("=")
        )

        return token, cluster_endpoint, cluster_cert
    except (BotoCoreError, ClientError, Exception) as e:
        logger.error(f"Error retrieving EKS token: {str(e)}")
        raise

def configure_k8s_client(cluster_name, region):
    """Configure Kubernetes client to interact with EKS cluster."""
    token, cluster_endpoint, cluster_cert = get_eks_token(cluster_name, region)
    logger.info("Token successfully retrieved for Kubernetes client configuration.")

    # Configure the Kubernetes client
    configuration = client.Configuration()
    configuration.host = cluster_endpoint
    configuration.verify_ssl = True
    configuration.api_key["authorization"] = f"Bearer {token}"

    # Write the certificate authority data to a temporary file
    ca_file = "/tmp/eks-ca.crt"
    with open(ca_file, "w") as cert_file:
        cert_file.write(base64.b64decode(cluster_cert).decode("utf-8"))
    configuration.ssl_ca_cert = ca_file

    # Set the default configuration
    client.Configuration.set_default(configuration)

def delete_pod(namespace, pod_name, cluster_name, region):
    """Delete a specific pod in the given namespace."""
    try:
        configure_k8s_client(cluster_name, region)  # Regenerate token before use
        v1 = client.CoreV1Api()
        logger.info(f"Attempting to delete pod: {pod_name} in namespace: {namespace}")
        response = v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Successfully deleted pod: {pod_name}. Response: {response}")
    except ApiException as e:
        logger.error(f"Error deleting pod {pod_name} in namespace {namespace}: {e}")
        raise

def lambda_handler(event, context):
    """Main Lambda handler function."""
    try:
        cluster_name = os.getenv("EKS_CLUSTER_NAME")
        if not cluster_name:
            raise ValueError("EKS_CLUSTER_NAME environment variable is not set.")

        # Fetch pod details from the event
        pods_to_delete = event.get("pods", [])

        if not pods_to_delete:
            raise ValueError("No pods specified in the event.")

        for pod in pods_to_delete:
            namespace = pod.get("namespace")
            pod_name = pod.get("name")

            if not namespace or not pod_name:
                logger.warning("Namespace or pod name is missing in the event. Skipping.")
                continue

            delete_pod(namespace, pod_name, cluster_name, REGION)

        return {"status": "success"}
    except Exception as e:
        logger.error(f"Lambda function failed: {e}")
        return {"status": "error", "message": str(e)}
