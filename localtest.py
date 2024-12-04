import os
import json
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException

region = os.getenv('AWS_REGION')
eks_cluster_name = os.getenv('EKS_CLUSTER_NAME')
debug = os.getenv('DEBUG', 'false').lower() == 'true'

eks_client = boto3.client('eks', region_name=region)

def get_eks_cluster_info():
    try:
        response = eks_client.describe_cluster(name=eks_cluster_name)
        return response['cluster']
    except Exception as e:
        return {"error": f"Failed to describe the EKS cluster: {str(e)}"}

def create_kube_config(cluster_info):
    kube_config = client.Configuration()
    kube_config.host = f"https://{cluster_info['endpoint']}"
    kube_config.verify_ssl = True
    kube_config.ssl_ca_cert = '/tmp/ca.crt'

    try:
        with open('/tmp/ca.crt', 'w') as ca_file:
            ca_file.write(cluster_info['certificateAuthority']['data'])
    except IOError as e:
        return {"error": f"Failed to write CA certificate: {str(e)}"}

    kube_config.api_key['authorization'] = "Bearer " + os.getenv('KUBE_TOKEN')
    client.Configuration.set_default(kube_config)

def delete_pod(namespace, pod_name):
    # Allowed namespaces
    allowed_namespaces = ['dev', 'sqlpad']

    if namespace not in allowed_namespaces:
        return {"error": f"Namespace '{namespace}' is not allowed. Allowed namespaces: {', '.join(allowed_namespaces)}"}

    # Load kube config from the local machine for testing
    config.load_kube_config()
    v1 = client.CoreV1Api()
    try:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return f"Pod {pod_name} deleted in namespace {namespace}."
    except ApiException as e:
        return {"error": f"API Exception occurred: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to delete pod: {str(e)}"}

def lambda_handler(event, context):
    namespace = event.get('namespace')
    pod_name = event.get('podName')

    # Validate input parameters
    if not namespace:
        return {"statusCode": 400, "body": "Error: 'namespace' parameter is required."}
    if not pod_name:
        return {"statusCode": 400, "body": "Error: 'podName' parameter is required."}

    cluster_info = get_eks_cluster_info()
    if isinstance(cluster_info, dict) and 'error' in cluster_info:
        return {"statusCode": 500, "body": cluster_info['error']}

    # Commenting out the following line for local testing
    # create_kube_config_response = create_kube_config(cluster_info)
    # if isinstance(create_kube_config_response, dict) and 'error' in create_kube_config_response:
    #     return {"statusCode": 500, "body": create_kube_config_response['error']}

    # Skipping the creation of kube config for local testing
    # Using the local kubeconfig directly instead
    result = delete_pod(namespace, pod_name)
    if isinstance(result, dict) and 'error' in result:
        return {"statusCode": 500, "body": result['error']}

    return {"statusCode": 200, "body": result}

if __name__ == "__main__":
    # Simulated Lambda event for local testing
    event = {
        "namespace": "dev",  # Choose one of the allowed namespaces
        "podName": "example-pod-name"  # Replace with the actual pod name
    }
    result = lambda_handler(event, None)
    print(result)
