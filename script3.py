import os
import logging
import boto3
from kubernetes import client
from kubernetes.client.rest import ApiException
import base64  # Ensure base64 is imported

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_eks_token(cluster_name, region):
    """
    Retrieve the token for authenticating with an EKS cluster using boto3.
    """
    try:
        logger.info(f"Generating token for cluster: {cluster_name}")
        eks_client = boto3.client('eks', region_name=region)
        cluster_info = eks_client.describe_cluster(name=cluster_name)
        cluster_endpoint = cluster_info['cluster']['endpoint']
        cluster_cert = cluster_info['cluster']['certificateAuthority']['data']

        # Generate the token using STS
        sts_client = boto3.client('sts', region_name=region)
        caller_identity = sts_client.get_caller_identity()
        token = (
            f"k8s-aws-v1."
            + base64.urlsafe_b64encode(
                f"{caller_identity['Arn']}:{caller_identity['Account']}".encode()
            ).decode().rstrip("=")
        )
        return token, cluster_endpoint, cluster_cert
    except Exception as e:
        logger.error(f"Error generating EKS token: {str(e)}")
        raise

def configure_k8s_client(cluster_name, region):
    """
    Configure Kubernetes client to interact with the EKS cluster.
    """
    try:
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
        region = os.getenv("AWS_REGION")
        if not cluster_name or not region:
            raise ValueError("EKS_CLUSTER_NAME and AWS_REGION environment variables must be set.")

        # Configure Kubernetes client
        configure_k8s_client(cluster_name, region)

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
