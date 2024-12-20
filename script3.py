import os
import logging
import boto3
import base64
from kubernetes import client
from kubernetes.client.rest import ApiException

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_eks_token(cluster_name, region):
    """Retrieve an EKS authentication token using AWS STS."""
    try:
        eks_client = boto3.client('eks', region_name=region)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        endpoint = cluster_info['cluster']['endpoint']
        ca_cert = cluster_info['cluster']['certificateAuthority']['data']

        # Generate the token
        sts_client = boto3.client('sts', region_name=region)
        identity = sts_client.get_caller_identity()
        arn = identity['Arn']
        token = f"k8s-aws-v1." + base64.urlsafe_b64encode(f"{arn}".encode()).decode().rstrip("=")

        return token, endpoint, ca_cert
    except Exception as e:
        logger.error(f"Error retrieving EKS token: {e}")
        raise

def configure_k8s_client(cluster_name, region):
    """Configure the Kubernetes client."""
    token, endpoint, ca_cert = get_eks_token(cluster_name, region)

    configuration = client.Configuration()
    configuration.host = endpoint
    configuration.verify_ssl = True
    configuration.api_key["authorization"] = f"Bearer {token}"
    configuration.ssl_ca_cert = "/tmp/ca.crt"

    # Write CA certificate to a file
    with open(configuration.ssl_ca_cert, "w") as cert_file:
        cert_file.write(base64.b64decode(ca_cert).decode("utf-8"))

    client.Configuration.set_default(configuration)

def delete_pod(namespace, pod_name):
    """Delete a pod in a namespace."""
    try:
        v1 = client.CoreV1Api()
        logger.info(f"Deleting pod {pod_name} in namespace {namespace}...")
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info(f"Successfully deleted pod {pod_name}.")
    except ApiException as e:
        logger.error(f"Failed to delete pod {pod_name}: {str(e)}")
        raise

def lambda_handler(event, context):
    """Main Lambda function."""
    cluster_name = os.getenv("EKS_CLUSTER_NAME")
    region = os.getenv("AWS_REGION")

    if not cluster_name or not region:
        logger.error("EKS_CLUSTER_NAME or AWS_REGION environment variable is missing.")
        return {"status": "error", "message": "Environment variables missing"}

    try:
        configure_k8s_client(cluster_name, region)

        pods_to_delete = event.get("pods", [])
        for pod in pods_to_delete:
            namespace = pod.get("namespace")
            name = pod.get("name")
            if namespace and name:
                delete_pod(namespace, name)
            else:
                logger.warning("Pod details are missing. Skipping.")
        return {"status": "success", "message": "Pods deleted successfully"}
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "message": str(e)}
