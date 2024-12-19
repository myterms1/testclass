# Use AWS Lambda Python Base Image
FROM public.ecr.aws/lambda/python:3.9

# Arguments for AWS IAM Authenticator version and platform
ARG AWS_IAM_AUTH_VERSION=0.6.14
ARG AWS_IAM_AUTH_PLATFORM=linux_amd64

# Add Zscaler CA Certificate to Trusted Store
COPY zscaler.pem /etc/ssl/certs/zscaler.pem
RUN cat /etc/ssl/certs/zscaler.pem >> /etc/ssl/certs/ca-certificates.crt

# Install AWS IAM Authenticator
RUN mkdir -p /usr/local/bin \
  && curl --cacert /etc/ssl/certs/ca-certificates.crt \
      -fsSL https://github.com/kubernetes-sigs/aws-iam-authenticator/releases/download/v${AWS_IAM_AUTH_VERSION}/aws-iam-authenticator_${AWS_IAM_AUTH_VERSION}_${AWS_IAM_AUTH_PLATFORM} \
      -o /usr/local/bin/aws-iam-authenticator \
  && chmod a+rx /usr/local/bin/aws-iam-authenticator

# Install Additional Utilities
RUN yum install -y vim unzip \
  && curl --cacert /etc/ssl/certs/ca-certificates.crt \
      -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" \
      -o "awscliv2.zip" \
  && unzip awscliv2.zip \
  && ./aws/install \
  && rm -rf aws awscliv2.zip

# Copy the Python script and requirements
COPY recycling_pod_script.py ${LAMBDA_TASK_ROOT}/
COPY requirements.txt .

# Install Python Libraries
RUN pip install --no-cache-dir -r requirements.txt

# Set Lambda Handler
CMD [ "recycling_pod_script.lambda_handler" ]
