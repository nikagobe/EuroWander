[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Paste the upload_url you got from Swagger here
$uploadUrl = "https://eurowander-documents-2026.s3.eu-north-1.amazonaws.com/trips/6a27fb13a4287d42674e8884/ca48124bdffc/test.pdf?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIASPLOU6JPPM4R4JF4%2F20260611%2Feu-north-1%2Fs3%2Faws4_request&X-Amz-Date=20260611T065732Z&X-Amz-Expires=3600&X-Amz-SignedHeaders=content-type%3Bhost&X-Amz-Signature=409d959474762514860920107215e59faa0c69ae3843552bf07d40f1f580303d"

# Path to your PDF file
$filePath = "C:\Users\Nikoloz.Gobejishvili\Downloads\test.pdf"

try {
    $bytes = [System.IO.File]::ReadAllBytes($filePath)
    $response = Invoke-WebRequest -Uri $uploadUrl -Method Put `
        -ContentType "application/pdf" `
        -Body $bytes
    Write-Host "SUCCESS! Status: $($response.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "FAILED! Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
    $errorBody = $reader.ReadToEnd()
    Write-Host $errorBody
}

