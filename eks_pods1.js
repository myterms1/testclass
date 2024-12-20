const { EKSClient, DescribeClusterCommand } = require("@aws-sdk/client-eks");
const k8s = require("@kubernetes/client-node");

const region = "us-east-1"; // Set your region here
const eksClusterName = process.env.EKS_CLUSTER_NAME; // Read from environment variable

// Initialize Kubernetes API client
let k8sCoreV1Api;

// Handler function
exports.handler = async (event) => {
    try {
        console.log("Received event:", JSON.stringify(event));

        // Initialize Kubernetes client only once
        if (!k8sCoreV1Api) {
            console.log("Initializing Kubernetes API client...");
            await initializeK8sClient();
        }

        const podsToDelete = event?.pods;
        if (!podsToDelete || podsToDelete.length === 0) {
            throw new Error("No pods provided in the event");
        }

        for (const pod of podsToDelete) {
            const podName = pod?.name;
            const namespace = pod?.namespace;

            if (!podName || !namespace) {
                throw new Error("Missing 'name' or 'namespace' for pod in event data");
            }

            console.log(`Attempting to delete pod: ${podName} in namespace: ${namespace}`);

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

// Function to initialize Kubernetes client
async function initializeK8sClient() {
    const eks = new EKSClient({ region });
    const describeClusterCommand = new DescribeClusterCommand({ name: eksClusterName });
    const clusterResponse = await eks.send(describeClusterCommand);
    const cluster = clusterResponse?.cluster;

    if (!cluster) {
        throw new Error("Failed to retrieve EKS cluster information");
    }

    console.log("EKS Cluster retrieved:", cluster);

    const kc = new k8s.KubeConfig();
    kc.loadFromOptions({
        clusters: [
            {
                name: eksClusterName,
                server: cluster.endpoint,
                caData: cluster.certificateAuthority?.data,
            },
        ],
        users: [
            {
                name: "lambda-user",
                exec: {
                    apiVersion: "client.authentication.k8s.io/v1beta1",
                    command: "aws",
                    args: [
                        "eks",
                        "get-token",
                        "--cluster-name",
                        eksClusterName,
                        "--region",
                        region,
                    ],
                    env: [
                        {
                            name: "AWS_REGION",
                            value: region,
                        },
                    ],
                },
            },
        ],
        contexts: [
            {
                name: "eks-context",
                cluster: eksClusterName,
                user: "lambda-user",
            },
        ],
        currentContext: "eks-context",
    });

    k8sCoreV1Api = kc.makeApiClient(k8s.CoreV1Api);
}
