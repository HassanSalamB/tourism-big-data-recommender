# Kubernetes Guide

You do not need Kubernetes for local development, demos, or a single-machine release. Docker Compose is enough for those cases.

Use Kubernetes when you need:

- a shared environment for multiple users
- independent scaling of API, dashboard, Airflow, Spark workers, and Kafka
- production-style rollouts and restarts
- managed secrets and config maps
- persistent volumes managed by a cluster
- cloud load balancers or ingress

## Recommended Kubernetes Approach

Do not hand-write every manifest for this stack first. Use mature Helm charts:

- Airflow: official Apache Airflow Helm chart
- Kafka: Bitnami Kafka chart or a managed Kafka service
- Spark: Spark Operator or managed Spark
- Postgres: managed Postgres in cloud, or a Postgres operator
- Neo4j: Neo4j Helm chart
- Prometheus/Grafana: kube-prometheus-stack
- App/API/dashboard: small custom Deployments and Services

## Minimal App Manifests

The app image can be deployed with a Deployment and Service. Example shape:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: holiday-api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: holiday-api
  template:
    metadata:
      labels:
        app: holiday-api
    spec:
      containers:
        - name: api
          image: your-dockerhub-username/holiday-itinerary:main
          command: ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
          ports:
            - containerPort: 8000
          envFrom:
            - secretRef:
                name: holiday-secrets
            - configMapRef:
                name: holiday-config
---
apiVersion: v1
kind: Service
metadata:
  name: holiday-api
spec:
  selector:
    app: holiday-api
  ports:
    - port: 8000
      targetPort: 8000
```

## Practical Recommendation

For this project, use:

1. Docker Compose for local and evaluator/demo distribution.
2. Docker Hub images from GitHub Actions.
3. Terraform for Snowflake/cloud warehouse setup.
4. Kubernetes only if deploying to a real shared cloud environment.
