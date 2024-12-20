const { EKSClient, DescribeClusterCommand } = require("@aws-sdk/client-eks");
const k8s = require("@kubernetes/client-node");

const region = "us-east-1"; // Set your region here
const eksClusterName = process.env.EKS_CLUSTER_NAME; // Cluster name from environment variable

// Set up Kubernetes client
const configureK8sClient = async (eksClusterName) => {
  try {
    const eks = new EKSClient({ region });
    const describeClusterCommand = new DescribeClusterCommand({ name: eksClusterName });
    const describeClusterResponse = await eks.send(describeClusterCommand);
    const eksCluster = describeClusterResponse?.cluster;

    if (!eksCluster) {
      throw new Error("Failed to fetch EKS cluster details");
    }

    const k8sCluster = {
      name: eksClusterName,
      server: eksCluster.endpoint,
      caData: eksCluster.certificateAuthority.data,
    };

    const k8sUser = {
      name: "lambda-user",
      exec: {
        apiVersion: "client.authentication.k8s.io/v1beta1",
        command: "aws",
        args: ["eks", "get-token", "--cluster-name", eksClusterName],
        env: [
          {
            name: "AWS_DEFAULT_REGION",
            value: region,
          },
        ],
      },
    };

    const k8sContext = {
      name: "eks",
      cluster: k8sCluster.name,
      user: k8sUser.name,
    };

    const kc = new k8s.KubeConfig();
    kc.loadFromOptions({
      clusters: [k8sCluster],
      contexts: [k8sContext],
      users: [k8sUser],
      currentContext: k8sContext.name,
    });

    return kc;
  } catch (error) {
    console.error("Error configuring Kubernetes client:", error.message);
    throw error;
  }
};

// Lambda handler
exports.handler = async (event) => {
  try {
    if (!eksClusterName) {
      throw new Error("EKS_CLUSTER_NAME environment variable is not set");
    }

    const podsToDelete = event?.pods;
    if (!podsToDelete || podsToDelete.length === 0) {
      throw new Error("No pods provided in the event");
    }

    // Configure Kubernetes client
    const kc = await configureK8sClient(eksClusterName);
    const k8sCoreV1Api = kc.makeApiClient(k8s.CoreV1Api);

    for (const pod of podsToDelete) {
      const podName = pod?.name;
      const namespace = pod?.namespace;

      if (!podName || !namespace) {
        throw new Error("Missing 'name' or 'namespace' for pod in event data");
      }

      // Call the Kubernetes API to delete the pod
      await k8sCoreV1Api.deleteNamespacedPod(podName, namespace);
      console.log(`Successfully deleted pod: ${podName} in namespace: ${namespace}`);
    }

    return { status: "success" };
  } catch (error) {
    console.error("Error:", error.message);
    return { status: "error", message: error.message };
  }
};
