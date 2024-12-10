import boto3
import subprocess
from kubernetes import client, config
from kubernetes.client.rest import ApiException

# Cluster mapping for testing
CLUSTER_MAPPING = {
    "blue": "sky-eks-dev-cluster-blue",
    "green": "sky-eks-dev-cluster-green"
}

def fetch_clusters(region):
    """
    Fetch all EKS clusters in the specified region.
    """
    eks_client = boto3.client("eks", region_name=region)
    try:
        response = eks_client.list_clusters()
        return response.get("clusters", [])
    except Exception as e:
        raise Exception(f"Failed to list clusters: {str(e)}")

def update_kubeconfig(cluster_name, region):
    """
    Update kubeconfig for the specified cluster.
    """
    try:
        command = ["aws", "eks", "update-kubeconfig", "--region", region, "--name", cluster_name]
        subprocess.run(command, check=True)
        print(f"Kubeconfig updated for cluster: {cluster_name}")
    except subprocess.CalledProcessError as e:
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
        return {"error": f"API Exception occurred: {str(e)}"}
    except Exception as e:
        return {"error": f"Failed to recycle pod: {str(e)}"}

def lambda_handler(event, context):
    """
    Lambda function handler to recycle a Kubernetes pod.
    """
    region = event.get("region", "us-east-1")
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

    # Map cluster ID to cluster name
    cluster_name = CLUSTER_MAPPING.get(cluster_id)
    if not cluster_name:
        return {"statusCode": 400, "body": f"Error: Unknown clusterId '{cluster_id}'."}

    try:
        # Update kubeconfig for the selected cluster
        update_kubeconfig(cluster_name, region)

        # Perform Kubernetes operations
        config.load_kube_config()  # Load updated kubeconfig
        result = recycle_pod(namespace, pod_name)

        return {"statusCode": 200, "body": result}
    except Exception as e:
        return {"statusCode": 500, "body": str(e)}

if __name__ == "__main__":
    # Example event for local testing
    event = {
        "region": "us-east-1",
        "clusterId": "blue",         # Specify the cluster to use (e.g., 'blue' or 'green')
        "namespace": "default",     # Kubernetes namespace
        "podName": "example-pod"    # Pod name to recycle
    }

    # Simulate Lambda handler locally
    result = lambda_handler(event, None)
    print(result)
