import os
import json
import boto3
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Load environment variables
region = os.getenv('AWS_REGION')
eks_cluster_name = os.getenv('EKS_CLUSTER_NAME')
namespace = os.getenv('K8S_NAMESPACE')
debug = os.getenv('DEBUG', 'false').lower() == 'true'

# Initialize AWS EKS client
eks_client = boto3.client('eks', region_name=region)

def get_eks_cluster_info():
    response = eks_client.describe_cluster(name=eks_cluster_name)
    return response['cluster']

def create_kube_config(cluster_info):
    kube_config = client.Configuration()
    kube_config.host = f"https://{cluster_info['endpoint']}"
    kube_config.verify_ssl = True
    kube_config.ssl_ca_cert = '/tmp/ca.crt'
    with open('/tmp/ca.crt', 'w') as ca_file:
        ca_file.write(cluster_info['certificateAuthority']['data'])
    kube_config.api_key['authorization'] = "Bearer " + os.getenv('KUBE_TOKEN')
    client.Configuration.set_default(kube_config)

def delete_pods(pod_name=None):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    if pod_name:
        v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
        return f"Pod '{pod_name}' deleted."
    else:
        pods = v1.list_namespaced_pod(namespace=namespace).items
        for pod in pods:
            v1.delete_namespaced_pod(name=pod.metadata.name, namespace=namespace)
        return "All pods in namespace deleted."

def lambda_handler(event, context):
    pod_name = event.get('podName')
    delete_all = event.get('deleteAll', False)
    cluster_info = get_eks_cluster_info()
    create_kube_config(cluster_info)
    result = delete_pods(pod_name if not delete_all else None)
    return {"statusCode": 200, "body": result}