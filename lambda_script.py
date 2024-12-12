import boto3
import base64
from kubernetes import client, config
from kubernetes.client.rest import ApiException
import os
import json
import logging

# Load environment variables
REGION = os.environ.get("AWS_REGION")
CLUSTER_MAPPING = json.loads(os.getenv("CLUSTER_MAPPING", "{}"))
ALLOWED_NAMESPACES = json.loads(os.getenv("ALLOWED_NAMESPACES", "[]"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Configure logging
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger(__name__)

def update_kubeconfig_via_sdk(cluster_name, region):
    """
    Update kubeconfig for the specified cluster using boto3.
    """
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
    token: {os.environ.get('KUBE_TOKEN')}
"""
        with open("/tmp/kubeconfig", "w") as kubeconfig_file:
            kubeconfig_file.write(kubeconfig_content)
        os.environ["KUBECONFIG"] = "/tmp/kubeconfig"
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
        # Update kubeconfig for the selected cluster using boto3
        update_kubeconfig_via_sdk(cluster_name, REGION)

        # Perform Kubernetes operations
        config.load_kube_config()  # Load updated kubeconfig
        result = recycle_pod(namespace, pod_name)

        return {"statusCode": 200, "body": result}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}
