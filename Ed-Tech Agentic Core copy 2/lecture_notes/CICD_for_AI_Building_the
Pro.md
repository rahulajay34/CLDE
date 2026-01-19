# CI/CD for AI: Building the Production Pipeline

## I. Introduction to CI/CD for LLM Systems

### What is CI/CD?

**Continuous Integration/Continuous Deployment (CI/CD)** is an automated approach to building, testing, and deploying software changes. For **Large Language Models (LLMs)**, CI/CD pipelines are essential for:

- **Model versioning and reproducibility**
- **Automated testing** of model quality and performance
- **Safe deployment** with rollback capabilities
- **Monitoring and observability** in production
- **Compliance and governance** for AI systems

### Why CI/CD Matters for LLMs

Unlike traditional software, LLM systems require specialized considerations:

- **Model drift**: Performance degrades over time
- **Inference variability**: Outputs may differ between runs
- **Resource constraints**: GPU/memory limitations during deployment
- **Safety concerns**: Hallucinations and biased outputs must be detected
- **Multi-component systems**: Models + prompts + embeddings + retrievers

---

## II. Architecture of an End-to-End LLM CI/CD Pipeline

### High-Level Pipeline Stages

```
Code Commit → Build → Unit Tests → Model Tests → 
Integration Tests → Staging Deploy → Production Deploy → 
Monitoring & Feedback
```

### Key Pipeline Components

| Stage | Purpose | Tools |
|-------|---------|-------|
| **Source Control** | Version code and models | Git, DVC, MLflow |
| **Build** | Package artifacts | Docker, Containerization |
| **Test** | Validate quality | Pytest, Custom frameworks |
| **Deploy** | Release to environments | Kubernetes, Cloud platforms |
| **Monitor** | Track performance | Prometheus, DataDog, Custom logs |

---

## III. Setting Up Version Control for LLM Projects

### Code and Model Versioning

**Git** tracks code, but models are large. Use **Data Version Control (DVC)**:

```bash
# Initialize DVC
dvc init
dvc remote add -d myremote s3://bucket/path

# Track model files
dvc add models/llm_v1.pkl
git add models/llm_v1.pkl.dvc
git commit -m "Add LLM v1"

# Retrieve specific model version
dvc checkout models/llm_v1.pkl.dvc
```

### Model Registry Pattern

Implement a **Model Registry** to track:

- Model name, version, and artifact location
- Performance metrics
- Training parameters
- Deployment status

```python
# Example: MLflow Model Registry
import mlflow.pyfunc

# Log model
mlflow.log_model(
    python_model=llm_wrapper,
    artifact_path="models",
    registered_model_name="production-llm"
)

# Transition to production
client = mlflow.tracking.MlflowClient()
client.transition_model_version_stage(
    name="production-llm",
    version=2,
    stage="Production"
)
```

---

## IV. Building and Containerization

### Docker for LLM Deployment

Create a **Dockerfile** for reproducible deployments:

```dockerfile
FROM pytorch/pytorch:2.0-cuda11.8-runtime-ubuntu22.04

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy model and application code
COPY models/ ./models/
COPY src/ ./src/

# Expose API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD curl -f http://localhost:8000/health || exit 1

# Run inference server
CMD ["python", "-m", "uvicorn", "src.api:app", "--host", "0.0.0.0"]
```

### Multi-Stage Builds for Optimization

```dockerfile
# Stage 1: Builder
FROM pytorch/pytorch:2.0 as builder
RUN pip install pyinstaller
COPY src/ /src/
RUN pyinstaller --onefile /src/inference.py

# Stage 2: Runtime (lightweight)
FROM pytorch/pytorch:2.0-runtime
COPY --from=builder /dist/inference /app/
CMD ["/app/inference"]
```

### Build Automation

```yaml
# .gitlab-ci.yml or GitHub Actions
name: Build and Push Image

on: [push]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: docker/build-push-action@v4
        with:
          push: true
          tags: registry.example.com/llm:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## V. Comprehensive Testing Strategy

### Unit Tests: Code Quality

```python
# tests/test_preprocessing.py
import pytest
from src.preprocessing import tokenize_input

def test_tokenize_basic():
    result = tokenize_input("Hello world")
    assert len(result) == 2
    assert result[0] == "hello"

def test_tokenize_empty():
    result = tokenize_input("")
    assert result == []

def test_tokenize_special_chars():
    result = tokenize_input("What's your name?")
    assert "?" not in result
```

### Model Quality Tests

Test for hallucinations, bias, and output validity:

```python
# tests/test_model_quality.py
import pytest
from src.llm_wrapper import LLMEndpoint

@pytest.fixture
def llm():
    return LLMEndpoint(model_path="models/llm_v1")

def test_factual_consistency(llm):
    """Verify model produces consistent facts"""
    question = "What is the capital of France?"
    responses = [llm.generate(question) for _ in range(5)]
    
    # Check consistency
    assert all("Paris" in r for r in responses)

def test_no_hallucination(llm):
    """Detect fabricated information"""
    prompt = "Explain quantum entanglement in simple terms"
    response = llm.generate(prompt)
    
    # Check against fact base
    facts = load_knowledge_base()
    assert validate_against_facts(response, facts)

def test_bias_detection(llm):
    """Check for demographic bias"""
    test_cases = [
        "Recommend a doctor",
        "Recommend an engineer",
        "Recommend a nurse"
    ]
    
    for prompt in test_cases:
        response = llm.generate(prompt)
        bias_score = measure_gender_bias(response)
        assert bias_score < 0.15  # Threshold

def test_response_latency(llm):
    """Ensure inference meets SLA"""
    import time
    start = time.time()
    llm.generate("Hello, how are you?")
    elapsed = time.time() - start
    assert elapsed < 1.0  # 1 second SLA
```

### Integration Tests: Component Interaction

```python
# tests/test_integration.py
def test_full_inference_pipeline():
    """Test: prompt → retriever → llm → response"""
    from src.retriever import DocumentRetriever
    from src.llm_wrapper import LLMEndpoint
    
    retriever = DocumentRetriever(index_path="indexes/prod")
    llm = LLMEndpoint(model_path="models/llm_v1")
    
    # RAG pipeline
    query = "What is machine learning?"
    docs = retriever.search(query, top_k=5)
    assert len(docs) > 0
    
    context = "\n".join([d.text for d in docs])
    response = llm.generate(f"Context: {context}\nQuestion: {query}")
    
    assert len(response) > 50
    assert "learning" in response.lower()

def test_api_endpoint():
    """Test REST API integration"""
    from fastapi.testclient import TestClient
    from src.api import app
    
    client = TestClient(app)
    response = client.post(
        "/v1/completions",
        json={"prompt": "Explain AI", "max_tokens": 100}
    )
    
    assert response.status_code == 200
    assert "choices" in response.json()
```

### Performance and Load Tests

```python
# tests/test_performance.py
import pytest
from locust import HttpUser, task

class LLMLoadTest(HttpUser):
    wait_time = lambda self: 1
    
    @task
    def generate(self):
        self.client.post(
            "/v1/completions",
            json={"prompt": "Hello", "max_tokens": 50}
        )

# Run: locust -f tests/test_performance.py --host http://localhost:8000
```

---

## VI. Continuous Integration Implementation

### GitHub Actions Pipeline

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Lint and format
        run: |
          black --check src/
          flake8 src/ --max-line-length=100
          mypy src/
      
      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src
      
      - name: Download model artifacts
        run: dvc pull models/llm_v1
      
      - name: Run model quality tests
        run: pytest tests/model/ -v
      
      - name: Build Docker image
        run: docker build -t llm:${{ github.sha }} .
      
      - name: Run container tests
        run: |
          docker run -d -p 8000:8000 llm:${{ github.sha }}
          sleep 5
          pytest tests/integration/ -v
      
      - name: Push to registry
        if: github.ref == 'refs/heads/main'
        run: |
          docker tag llm:${{ github.sha }} registry.example.com/llm:latest
          docker push registry.example.com/llm:latest
```

### GitLab CI Alternative

```yaml
# .gitlab-ci.yml
stages:
  - test
  - build
  - deploy

variables:
  REGISTRY: registry.gitlab.com
  IMAGE_NAME: $REGISTRY/$CI_PROJECT_PATH

test:
  stage: test
  image: python:3.10
  script:
    - pip install -r requirements.txt
    - pytest tests/ -v --cov=src
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml

build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t $IMAGE_NAME:$CI_COMMIT_SHA .
    - docker push $IMAGE_NAME:$CI_COMMIT_SHA
  only:
    - main
```

---

## VII. Deployment Strategies

### Kubernetes Deployment

Define reproducible production environments:

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-endpoint
  namespace: production
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: llm-endpoint
  template:
    metadata:
      labels:
        app: llm-endpoint
    spec:
      containers:
      - name: llm
        image: registry.example.com/llm:v1.2.0
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: "1"
          limits:
            memory: "24Gi"
            cpu: "8"
            nvidia.com/gpu: "1"
        env:
        - name: MODEL_PATH
          value: /models/llm_v1
        - name: LOG_LEVEL
          value: "INFO"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 5
```

### Canary Deployments

Gradually roll out new model versions:

```yaml
# k8s/canary.yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: llm-endpoint
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: llm-endpoint
  progressDeadlineSeconds: 300
  service:
    port: 8000
  analysis:
    interval: 1m
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99
    - name: request-duration
      thresholdRange:
        max: 500
    webhooks:
    - name: acceptance-test
      url: http://flagger-loadtester/
      metadata:
        type: bash
        cmd: "curl -s http://llm-endpoint:8000/health"
```

### Blue-Green Deployments

```python
# scripts/deploy_blue_green.py
import boto3

def deploy_blue_green(new_image_uri):
    """Deploy with immediate rollback capability"""
    ecs = boto3.client('ecs')
    
    # Create new task definition (green)
    new_task = ecs.register_task_definition(
        family='llm-endpoint',
        containerDefinitions=[{
            'name': 'llm',
            'image': new_image_uri,
            'cpu': 2048,
            'memory': 8192,
            'portMappings': [{'containerPort': 8000}]
        }]
    )
    
    # Update service to use green
    ecs.update_service(
        cluster='production',
        service='llm-endpoint',
        taskDefinition=f"llm-endpoint:{new_task['taskDefinition']['revision']}"
    )
    
    # Run tests against green
    if not run_smoke_tests('http://green.llm-endpoint:8000'):
        rollback(previous_task_definition)
        return False
    
    return True
```

---

## VIII. Continuous Monitoring and Observability

### Key Metrics for LLM Endpoints

```python
# src/monitoring.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
request_count = Counter(
    'llm_requests_total',
    'Total requests',
    ['method', 'status']
)

request_latency = Histogram(
    'llm_request_duration_seconds',
    'Request latency',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0]
)

# Model quality metrics
hallucination_rate = Gauge(
    'llm_hallucination_rate',
    'Proportion of hallucinated responses'
)

token_usage = Counter(
    'llm_tokens_used_total',
    'Total tokens consumed',
    ['model', 'type']  # type: prompt, completion
)

# System metrics
gpu_utilization = Gauge(
    'llm_gpu_utilization',
    'GPU memory usage percentage'
)

inference_queue_length = Gauge(
    'llm_inference_queue_length',
    'Pending inference requests'
)
```

### Instrumentation in API

```python
# src/api.py
from fastapi import FastAPI
from prometheus_client import generate_latest
import time

app = FastAPI()

@app.post("/v1/completions")
async def completions(request: CompletionRequest):
    start = time.time()
    
    try:
        response = llm.generate(
            prompt=request.prompt,
            max_tokens=request.max_tokens
        )
        
        request_count.labels(
            method='POST',
            status='success'
        ).inc()
        
        # Track tokens
        token_usage.labels(
            model='llm-v1',
            type='prompt'
        ).inc(len(request.prompt.split()))
        
        token_usage.labels(
            model='llm-v1',
            type='completion'
        ).inc(len(response.split()))
        
    except Exception as e:
        request_count.labels(
            method='POST',
            status='error'
        ).inc()
        raise
    
    finally:
        elapsed = time.time() - start
        request_latency.observe(elapsed)
    
    return {"choices": [{"text": response}]}

@app.get("/metrics")
async def metrics():
    return generate_latest()
```

### Logging and Alerting

```python
# src/logging_config.py
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_obj)

# Configure structured logging
logger = logging.getLogger('llm-endpoint')
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### Drift Detection

```python
# src/drift_detector.py
import numpy as np
from scipy import stats

class ModelDriftDetector:
    def __init__(self, baseline_metrics):
        self.baseline = baseline_metrics
    
    def check_drift(self, current_metrics):
        """Kolmogorov-Smirnov test for distribution shift"""
        for metric_name, baseline_dist in self.baseline.items():
            current_dist = current_metrics[metric_name]
            
            statistic, p_value = stats.ks_2samp(
                baseline_dist,
                current_dist
            )
            
            if p_value < 0.05:  # Significant drift
                logger.warning(
                    f"Drift detected in {metric_name}: "
                    f"KS statistic={statistic:.3f}, p-value={p_value:.4f}"
                )
                return True
        
        return False
```

---

## IX. Feedback Loops and Continuous Improvement

### Collecting Production Insights

```python
# src/feedback_collector.py
class FeedbackCollector:
    def __init__(self, db_connection):
        self.db = db_connection
    
    def log_prediction(self, request_id, prompt, response, metadata):
        """Log all predictions for analysis"""
        self.db.insert('predictions', {
            'request_id': request_id,
            'prompt': prompt,
            'response': response,
            'timestamp': datetime.now(),
            'latency_ms': metadata['latency'],
            'tokens_used': metadata['tokens'],
            'model_version': metadata['model_version']
        })
    
    def log_feedback(self, request_id, feedback, rating):
        """Capture human feedback"""
        self.db.insert('feedback', {
            'request_id': request_id,
            'feedback_text': feedback,
            'rating': rating,  # 1-5 stars
            'timestamp': datetime.now()
        })
    
    def get_low_quality_predictions(self, threshold=2.0):
        """Identify predictions for retraining"""
        return self.db.query('''
            SELECT p.* FROM predictions p
            JOIN feedback f ON p.request_id = f.request_id
            WHERE f.rating < ? AND f.timestamp > now() - interval 7 day
        ''', [threshold])
```

### Data Pipeline for Retraining

```yaml
# airflow/dags/llm_retraining_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'ml-team',
    'retries': 2,
    'retry_delay': timedelta(hours=1)
}

with DAG(
    'llm_retraining',
    default_args=default_args,
    schedule_interval='0 2 * * 0',  # Weekly
    start_date=datetime(2024, 1, 1)
) as dag:
    
    def collect_feedback():
        """Task 1: Gather low-quality predictions"""
        collector = FeedbackCollector()
        low_quality = collector.get_low_quality_predictions()
        return low_quality.to_json()
    
    def prepare_training_data(ti):
        """Task 2: Format data for training"""
        low_quality = ti.xcom_pull(task_ids='collect_feedback')
        # Clean, augment, split data
        pass
    
    def finetune_model(ti):
        """Task 3: Finetune on new data"""
        training_data = ti.xcom_pull(task_ids='prepare_training_data')
        new_model = train_llm(training_data)
        mlflow.log_model(new_model, artifact_path="models")
    
    def evaluate_model(ti):
        """Task 4: Test on holdout set"""
        model_uri = ti.xcom_pull(task_ids='finetune_model')
        metrics = evaluate(model_uri)
        return metrics
    
    def promote_if_improved(ti):
        """Task 5: Conditional promotion"""
        new_metrics = ti.xcom_pull(task_ids='evaluate_model')
        if new_metrics['accuracy'] > baseline_accuracy * 1.02:
            promote_model_to_staging(new_metrics)
    
    collect_feedback() >> prepare_training_data() >> \
    finetune_model() >> evaluate_model() >> promote_if_improved()
```

---

## X. Best Practices and Production Checklist

### Pre-Deployment Checklist

- [ ] **Code Review**: Peer review of model, inference, and pipeline code
- [ ] **Test Coverage**: >80% unit test coverage
- [ ] **Security Scan**: Check for vulnerabilities (Bandit, Snyk)
- [ ] **Model Card**: Document model behavior, limitations, and biases
- [ ] **Performance Baseline**: Establish latency/throughput requirements
- [ ] **Rollback Plan**: Document rollback procedures
- [ ] **Cost Estimation**: Compute infrastructure costs
- [ ] **Compliance Check**: GDPR, bias audits, data privacy

### Production Readiness Standards

```python
# Production standards
PRODUCTION_STANDARDS = {
    'availability': 0.999,  # 99.9% uptime
    'p95_latency_ms': 500,
    'hallucination_rate': '<5%',
    'test_coverage': '>80%',
    'documented_models': True,
    'monitoring_enabled': True,
    'alerting_configured': True,
    'rollback_tested': True,
    'cost_monitored': True
}
```

### Security Hardening

```dockerfile
# Security-hardened Dockerfile
FROM python:3.10-slim

# Run as non-root
RUN useradd -m -u 1000 llmuser

WORKDIR /app

# Copy with correct permissions
COPY --chown=llmuser:llmuser . .

# Minimal dependencies
RUN pip install --no-cache-dir \
    --only-binary=:all: \
    -r requirements.txt

USER llmuser

# Read-only filesystem
SECURITY_OPT="--read-only"

CMD ["python", "-m", "uvicorn", "api:app"]
```

---

## Conclusion

An effective CI/CD pipeline for LLMs requires:

1. **Robust versioning** of code, models, and data
2. **Comprehensive testing** across code quality, model behavior, and integration
3. **Automated deployment** with safety mechanisms (canary, blue-green)
4. **Production observability** with drift detection and feedback loops
5. **Continuous improvement** through data collection and retraining

By implementing these practices, organizations can deploy LLMs reliably, monitor their performance in production, and iterate rapidly while maintaining quality and safety standards.