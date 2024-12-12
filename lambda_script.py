import boto3
import base64
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import json
import logging
import time

# Load environment variables
REGION = os.environ.get("AWS_REGION", "us-east-1")
CLUSTER_MAPPING = json.loads(os.getenv("CLUSTER_MAPPING", "{}"))
ALLOWED_NAMESPACES = json.loads(os.getenv("ALLOWED_NAMESPACES", "[]"))
KUBE_TOKEN = os.getenv("KUBE_TOKEN")  # Kubernetes Bearer Token
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(level=LOG_LEVEL, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def log_step(step_message):
    """
    Log the current step with a timestamp for debugging.
    """
    logger.info(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {step_message}")

def update_kubeconfig_via_sdk(cluster_name, region):
    """
    Update kubeconfig for the specified cluster using boto3.
    """
    kubeconfig_path = "/tmp/kubeconfig"
    if os.path.exists(kubeconfig_path):
        logger.info(f"Kubeconfig already exists at {kubeconfig_path}. Skipping update.")
        return

    eks_client = boto3.client("eks", region_name=region)
    try:
        cluster_info = eks_client.describe_cluster(name=cluster_name)["cluster"]
        cluster_endpoint = cluster_info["endpoint"]
        cluster_cert = base64.b64decode(cluster_info["certificateAuthority"]["data"]).decode("utf-8")
        kubeconfig_content = f"""
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: {cluster_info['certificateAuthority']['data']}
    server: {cluster_endpoint}
  name: {cluster_name}
contexts:
- context:
    cluster: {cluster_name}
    user: {cluster_name}
  name: {cluster_name}
current-context: {cluster_name}
kind: Config
preferences: {{}}
users:
- name: {cluster_name}
  user:
    token: {KUBE_TOKEN}
"""
        with open(kubeconfig_path, "w") as kubeconfig_file:
            kubeconfig_file.write(kubeconfig_content)
        os.environ["KUBECONFIG"] = kubeconfig_path

        logger.info(f"Kubeconfig updated for cluster: {cluster_name}")
    except Exception as e:
        logger.error(f"Failed to update kubeconfig: {str(e)}")
        raise Exception(f"Failed to update kubeconfig: {str(e)}")

def recycle_pod(namespace, pod_name):
    """
    Delete the specified pod in the namespace.
    """
    v1 = client.CoreV1Api()
    try:
        log_step(f"Attempting to recycle pod {pod_name} in namespace {namespace}...")
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        log_step(f"Successfully recycled pod {pod_name} in namespace {namespace}.")
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
    log_step("Lambda handler invoked.")
    
    # Extract inputs
    cluster_id = event.get("clusterId")
    namespace = event.get("namespace")
    pod_name = event.get("podName")

    # Validate inputs
    if not cluster_id:
        logger.error("Missing 'clusterId' parameter.")
        return {"statusCode": 400, "body": "Error: 'clusterId' parameter is required."}
    if not namespace:
        logger.error("Missing 'namespace' parameter.")
        return {"statusCode": 400, "body": "Error: 'namespace' parameter is required."}
    if not pod_name:
        logger.error("Missing 'podName' parameter.")
        return {"statusCode": 400, "body": "Error: 'podName' parameter is required."}

    # Check namespace
    if namespace not in ALLOWED_NAMESPACES:
        logger.error(f"Namespace '{namespace}' is not allowed.")
        return {
            "statusCode": 400,
            "body": f"Error: Namespace '{namespace}' is not allowed. Allowed namespaces: {', '.join(ALLOWED_NAMESPACES)}"
        }

    # Map cluster ID to cluster name
    cluster_name = CLUSTER_MAPPING.get(cluster_id)
    if not cluster_name:
        logger.error(f"Unknown clusterId '{cluster_id}'.")
        return {"statusCode": 400, "body": f"Error: Unknown clusterId '{cluster_id}'."}

    try:
        # Update kubeconfig
        log_step("Starting kubeconfig update...")
        update_kubeconfig_via_sdk(cluster_name, REGION)

        # Perform Kubernetes operations
        log_step("Loading kubeconfig...")
        config.load_kube_config(config_file="/tmp/kubeconfig")
        log_step("Kubeconfig loaded successfully.")

        log_step("Recycling pod...")
        result = recycle_pod(namespace, pod_name)

        log_step("Pod recycling completed.")
        return {"statusCode": 200, "body": result}
    except Exception as e:
        logger.error(f"Error encountered: {str(e)}")
        return {"statusCode": 500, "body": str(e)}
