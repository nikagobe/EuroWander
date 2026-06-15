# Deploying EuroWander API to AWS Lambda

## Architecture

```
┌────────────────────────────────┐
│  API Gateway (HTTP API v2)     │  ← Public URL
└────────────┬───────────────────┘
             │ Lambda Proxy Event
┌────────────▼───────────────────┐
│  AWS Lambda (Container Image)  │
│  ┌──────────────────────────┐  │
│  │  Mangum (ASGI adapter)   │  │
│  │  ┌────────────────────┐  │  │
│  │  │  FastAPI (app)     │  │  │
│  │  └────────────────────┘  │  │
│  └──────────────────────────┘  │
└────────────┬───────────────────┘
             │ async Motor
┌────────────▼───────────────────┐
│  MongoDB Atlas                 │
└────────────────────────────────┘
```

## Prerequisites

1. **AWS CLI** – configured with credentials (`aws configure`)
2. **AWS SAM CLI** – [Install](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
3. **Docker Desktop** – running (SAM builds the container image locally)
4. **MongoDB Atlas** – your cluster must whitelist `0.0.0.0/0` (or Lambda's NAT IP)

## Quick Deploy (One Command)

Set environment variables first:

```powershell
$env:MONGODB_URI       = "mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true"
$env:SECRET_KEY        = "your-jwt-secret"
$env:SERPAPI_KEY       = ""
$env:RAPIDAPI_KEY      = ""
$env:GOOGLE_PLACES_KEY = ""
$env:AWS_S3_BUCKET_NAME = "eurowander-uploads"
$env:AWS_S3_REGION     = "eu-central-1"
```

Then run:

```powershell
.\scripts\deploy_lambda.ps1 -StackName "eurowander-api" -Region "eu-central-1"
```

## Manual Step-by-Step

### 1. Build

```powershell
sam build
```

This builds the Docker image defined in `Dockerfile.lambda`.

### 2. Deploy

```powershell
sam deploy --guided
```

SAM will ask for:
- Stack name → `eurowander-api`
- Region → `eu-central-1`
- Parameter values (MongoDB URI, secrets, etc.)
- Confirm IAM role creation → `Y`
- Allow SAM to create ECR repo → `Y`

### 3. Get Your URL

After deployment:

```powershell
sam list endpoints --stack-name eurowander-api --output table
```

Output example:
```
https://abc123xyz.execute-api.eu-central-1.amazonaws.com
```

Your Flutter app should point `baseUrl` to this.

## Local Testing (SAM Local)

Simulate Lambda locally:

```powershell
sam local start-api --env-vars env.json
```

Create `env.json`:
```json
{
  "EuroWanderFunction": {
    "MONGODB_URI": "mongodb://admin:secret@localhost:27017/eurowander?authSource=admin",
    "DATABASE_NAME": "eurowander",
    "SECRET_KEY": "dev-secret"
  }
}
```

## Updating After Code Changes

```powershell
sam build ; sam deploy --no-confirm-changeset
```

## Cold Starts & Performance Tips

| Setting | Recommendation |
|---------|---------------|
| Memory | 512 MB minimum (more RAM = more CPU) |
| Timeout | 30s (covers Motor cold-connect to Atlas) |
| Provisioned Concurrency | Set to 1-2 for production (eliminates cold starts) |
| Keep-Alive | MongoDB connection pooling handled by Motor across warm invocations |

## Costs (Estimate)

- **Lambda free tier:** 1M requests/month + 400,000 GB-seconds
- **API Gateway:** $1/million requests
- **ECR:** ~$0.10/GB/month for image storage
- For a travel app in early stage: essentially **free** or < $5/month.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Task timed out after 30s` | Increase timeout in `template.yaml`, or check MongoDB Atlas IP whitelist |
| `Cannot connect to MongoDB` | Ensure Atlas allows `0.0.0.0/0` or add Lambda's VPC NAT IP |
| `Module not found` | Verify `Dockerfile.lambda` copies all required source files |
| `502 Bad Gateway` | Check CloudWatch Logs: `sam logs --stack-name eurowander-api --tail` |

