const { EKSClient, DescribeClusterCommand } = require("@aws-sdk/client-eks");
const k8s = require("@kubernetes/client-node");

const region = "us-east-1"; // Set your AWS region here
const eksClusterName = process.env.EKS_CLUSTER_NAME;

let k8sCoreV1Api;

const initializeKubernetesClient = async () => {
    try {
        const eks = new EKSClient({ region });
        const describeClusterCommand = new DescribeClusterCommand({ name: eksClusterName });
        const describeClusterResponse = await eks.send(describeClusterCommand);
        const eksCluster = describeClusterResponse.cluster;

        console.log("EKS Cluster retrieved:", JSON.stringify(eksCluster, null, 2));

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
                args: [
                    "eks",
                    "get-token",
                    "--cluster-name",
                    eksClusterName,
                    "--region",
                    region,
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
            users: [k8sUser],
            contexts: [k8sContext],
            currentContext: k8sContext.name,
        });

        k8sCoreV1Api = kc.makeApiClient(k8s.CoreV1Api);
        console.log("Kubernetes API client initialized successfully.");
    } catch (error) {
        console.error("Error initializing Kubernetes client:", error.message);
        throw new Error("Failed to initialize Kubernetes client");
    }
};

exports.handler = async (event) => {
    try {
        console.log("Received event:", JSON.stringify(event));

        const podsToDelete = event?.pods;
        if (!podsToDelete || podsToDelete.length === 0) {
            throw new Error("No pods provided in the event");
        }

        // Initialize Kubernetes API client if not already initialized
        if (!k8sCoreV1Api) {
            console.log("Initializing Kubernetes API client...");
            await initializeKubernetesClient();
        }

        for (const pod of podsToDelete) {
            const podName = pod?.name;
            const namespace = pod?.namespace;

            console.log("Pod Name:", podName);
            console.log("Namespace:", namespace);

            if (!podName) {
                throw new Error("Pod name is null or undefined");
            }
            if (!namespace) {
                throw new Error("Namespace is null or undefined");
            }

            console.log(`Attempting to delete pod: ${podName} in namespace: ${namespace}`);

            await k8sCoreV1Api.deleteNamespacedPod(podName, namespace);
            console.log(`Successfully deleted pod: ${podName} in namespace: ${namespace}`);
        }

        return { status: "success" };
    } catch (error) {
        console.error("Error:", error.message);
        return { status: "error", message: error.message };
    }
};
