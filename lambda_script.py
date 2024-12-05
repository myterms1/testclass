import os
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Environment variables
region = os.getenv('AWS_REGION')
eks_cluster_name = os.getenv('EKS_CLUSTER_NAME')

# Allowed namespaces for pod recycling
allowed_namespaces = ['dev', 'sqlpad']

# Boto3 client for EKS
eks_client = boto3.client('eks', region_name=region)

def get_eks_cluster_info():
    """
    Fetch the details of the EKS cluster from AWS.
    """
    try:
        response = eks_client.describe_cluster(name=eks_cluster_name)
        return response['cluster']
    except Exception as e:
        return {"error": f"Failed to describe the EKS cluster: {str(e)}"}

def create_kube_config(cluster_info):
    """
    Create Kubernetes configuration dynamically for the EKS cluster.
    """
    kube_config = client.Configuration()
    kube_config.host = f"https://{cluster_info['endpoint']}"
    kube_config.verify_ssl = True
    kube_config.ssl_ca_cert = '/tmp/ca.crt'

    try:
        # Write the cluster's CA certificate to a temporary file
        with open('/tmp/ca.crt', 'w') as ca_file:
            ca_file.write(cluster_info['certificateAuthority']['data'])
    except IOError as e:
        return {"error": f"Failed to write CA certificate: {str(e)}"}

    kube_config.api_key['authorization'] = "Bearer " + os.getenv('KUBE_TOKEN')
    client.Configuration.set_default(kube_config)

def recycle_pod(namespace, pod_name):
    """
    Recycle (delete) a pod by name within a specific namespace.
    """
    if namespace not in allowed_namespaces:
        return {"error": f"Namespace '{namespace}' is not allowed. Allowed namespaces: {', '.join(allowed_namespaces)}"}

    # Load Kubernetes configuration
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return f"Pod {pod_name} recycled (deleted) in namespace {namespace}."
    except ApiException as e:
        return {"error": f"API Exception occurred: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to recycle pod: {str(e)}"}

def lambda_handler(event, context):
    """
    Lambda function handler to recycle a pod in a Kubernetes namespace.
    """
    namespace = event.get('namespace')
    pod_name = event.get('podName')

    # Validate input parameters
    if not namespace:
        return {"statusCode": 400, "body": "Error: 'namespace' parameter is required."}
    if not pod_name:
        return {"statusCode": 400, "body": "Error: 'podName' parameter is required."}

    # Fetch EKS cluster information
    cluster_info = get_eks_cluster_info()
    if isinstance(cluster_info, dict) and 'error' in cluster_info:
        return {"statusCode": 500, "body": cluster_info['error']}

    # Create Kubernetes configuration for the cluster
    create_kube_config_response = create_kube_config(cluster_info)
    if isinstance(create_kube_config_response, dict) and 'error' in create_kube_config_response:
        return {"statusCode": 500, "body": create_kube_config_response['error']}

    # Attempt to recycle the pod
    result = recycle_pod(namespace, pod_name)
    if isinstance(result, dict) and 'error' in result:
        return {"statusCode": 500, "body": result['error']}

    return {"statusCode": 200, "body": result}
