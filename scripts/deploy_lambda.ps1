<#
  EuroWander – Deploy to AWS Lambda via SAM CLI
  Prerequisites: AWS CLI configured, SAM CLI installed, Docker running.
#>

param(
    [string]$StackName = "eurowander-api",
    [string]$Region   = "eu-central-1",
    [string]$Profile  = "default"
)

Write-Host "=== Building SAM application (container image) ===" -ForegroundColor Cyan
sam build --use-container

if ($LASTEXITCODE -ne 0) {
    Write-Error "SAM build failed."
    exit 1
}

Write-Host "`n=== Deploying to AWS ($Region) ===" -ForegroundColor Cyan
sam deploy `
    --stack-name $StackName `
    --region $Region `
    --profile $Profile `
    --resolve-image-repos `
    --resolve-s3 `
    --capabilities CAPABILITY_IAM `
    --parameter-overrides `
        "MongoDbUri=$env:MONGODB_URI" `
        "SecretKey=$env:SECRET_KEY" `
        "SerpApiKey=$env:SERPAPI_KEY" `
        "RapidApiKey=$env:RAPIDAPI_KEY" `
        "GooglePlacesKey=$env:GOOGLE_PLACES_KEY" `
        "AwsS3BucketName=$env:AWS_S3_BUCKET_NAME" `
        "AwsS3Region=$env:AWS_S3_REGION" `
    --no-confirm-changeset

if ($LASTEXITCODE -ne 0) {
    Write-Error "SAM deploy failed."
    exit 1
}

Write-Host "`n=== Deployment complete! ===" -ForegroundColor Green
sam list endpoints --stack-name $StackName --region $Region --output table

