const { EKSClient, DescribeClusterCommand } = require("@aws-sdk/client-eks");
const k8s = require("@kubernetes/client-node");

const region = process.env.AWS_REGION || "us-east-1";
const eksClusterName = process.env.EKS_CLUSTER_NAME;
const namespace = process.env.NAMESPACE || "default";

exports.handler = async (event) => {
  try {
    // Step 1: Get EKS Cluster Information
    const eksClient = new EKSClient({ region });
    const describeClusterCommand = new DescribeClusterCommand({ name: eksClusterName });
    const { cluster } = await eksClient.send(describeClusterCommand);

    // Step 2: Configure Kubernetes Client
    const kubeConfig = new k8s.KubeConfig();
    kubeConfig.loadFromOptions({
      clusters: [{ name: eksClusterName, server: cluster.endpoint, caData: cluster.certificateAuthority.data }],
      users: [
        {
          name: "eks-user",
          exec: {
            command: "aws",
            args: ["eks", "get-token", "--cluster-name", eksClusterName],
            env: [{ name: "AWS_REGION", value: region }],
          },
        },
      ],
      contexts: [{ name: "eks-context", cluster: eksClusterName, user: "eks-user" }],
      currentContext: "eks-context",
    });

    const k8sApi = kubeConfig.makeApiClient(k8s.CoreV1Api);
    const podName = event.podName;
    const podNamespace = event.namespace || namespace;

    // Step 3: Delete the Pod
    await k8sApi.deleteNamespacedPod(podName, podNamespace);
    console.log(`Pod ${podName} in namespace ${podNamespace} deleted successfully.`);
    return { status: "success", message: `Pod ${podName} deleted successfully.` };
  } catch (error) {
    console.error("Error:", error);
    return { status: "error", message: error.message };
  }
};
