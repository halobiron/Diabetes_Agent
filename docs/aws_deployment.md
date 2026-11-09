# AWS Deployment

The deployment target is AWS App Runner running two Dockerized services:

- FastAPI inference API
- Next.js healthcare risk console

This keeps the production path small enough to maintain while still showing a real cloud
stack: Docker, ECR, managed HTTPS, health checks, Terraform, and token-protected APIs.

## Deployment Flow

1. Train locally with `scripts/train_diabetes_model.py`.
2. Verify `risk_model.joblib` exists in `artifacts/`.
3. Create the ECR repositories with Terraform.
4. Build the API and web Docker images.
5. Push both images to ECR.
6. Deploy both App Runner services with Terraform from `infra/aws/apprunner`.

## Runtime Contract

The container expects:

- `MODEL_ARTIFACT_PATH=/app/artifacts/risk_model.joblib`
- `REQUIRE_API_TOKEN=true`
- `API_TOKEN=<strong-token>`
- `OPENAI_API_KEY=<optional-key>`

The Next.js container expects:

- `API_BASE_URL=https://<api-service-url>`
- `API_TOKEN=<same-token-used-by-api>`

If the model artifact is not present, the service starts with the local demo CSV model.
For the portfolio deployment, include the locally trained artifact in the image before pushing
to ECR.

## API Checks

```bash
curl -s https://<service-url>/health
curl -s https://<service-url>/v1/predict/summary \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"age":52,"height_cm":170,"weight_kg":88,"bp":142,"glucose":160}'
```

## Web Check

Open the App Runner web service URL and run a patient assessment from the browser.
The browser calls the Next.js `/api/predict` route, and that server-side route forwards
to the protected FastAPI `/v1/predict` endpoint.

## Portfolio Talking Points

- reproducible local training
- persisted model artifact with metrics and model card
- FastAPI inference service
- Next.js production risk console
- retrieval, memory, safety checks, and explainability
- Dockerized deployment to AWS App Runner with Terraform
