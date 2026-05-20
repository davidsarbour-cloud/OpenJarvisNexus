# ============================================================
# setup-etsy-oauth.ps1 - VERSION CORRIGEE
# ============================================================

# Charger le .env
$envPath = Join-Path (Split-Path $PSScriptRoot) ".env"
Get-Content $envPath | ForEach-Object {
    if ($_ -match "^([^#][^=]*)=(.*)$") {
        [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim())
    }
}

$keystring   = [System.Environment]::GetEnvironmentVariable("ETSYPUBLIC_KEY")
$redirectUri = [System.Environment]::GetEnvironmentVariable("ETSY_OAUTH_REDIRECT_URI")
$scopes      = "listings_r listings_w shops_r shops_w"

Write-Host "Keystring: $keystring" -ForegroundColor Cyan

# ETAPE 1 : PKCE
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 32
$rng.GetBytes($bytes)
$codeVerifier = [Convert]::ToBase64String($bytes) -replace '\+','-' -replace '/','_' -replace '=',''

$sha256 = [System.Security.Cryptography.SHA256]::Create()
$challengeBytes = $sha256.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($codeVerifier))
$codeChallenge = [Convert]::ToBase64String($challengeBytes) -replace '\+','-' -replace '/','_' -replace '=',''

# Sauvegarder le verifier
$verifierPath = Join-Path $PSScriptRoot "..\config\etsy\pkce-verifier.txt"
New-Item -ItemType Directory -Force -Path (Split-Path $verifierPath) | Out-Null
$codeVerifier | Out-File -FilePath $verifierPath -Encoding UTF8
Write-Host "Verifier sauvegarde" -ForegroundColor Green

# ETAPE 2 : URL auth - AMPERSAND FIXE avec array
$params = @(
    "response_type=code",
    "client_id=$keystring",
    "redirect_uri=$([Uri]::EscapeDataString($redirectUri))",
    "scope=$([Uri]::EscapeDataString($scopes))",
    "code_challenge=$codeChallenge",
    "code_challenge_method=S256"
)
$authUrl = "https://www.etsy.com/oauth/connect?" + ($params -join "&")

Write-Host ""
Write-Host "OUVRE CE LIEN DANS TON NAVIGATEUR:" -ForegroundColor Yellow
Write-Host $authUrl -ForegroundColor White
Write-Host ""

# ETAPE 3 : Capturer le code
$redirectUrl = Read-Host "Colle l URL complete de redirection ici"

if ($redirectUrl -match "[?&]code=([^&]+)") {
    $authCode = $matches[1]
    Write-Host "Code extrait: $authCode" -ForegroundColor Green
} else {
    Write-Host "Impossible d extraire le code" -ForegroundColor Red
    exit 1
}

# ETAPE 4 : Echange token - AMPERSAND FIXE avec array
$bodyParts = @(
    "grant_type=authorization_code",
    "client_id=$keystring",
    "redirect_uri=$([Uri]::EscapeDataString($redirectUri))",
    "code=$authCode",
    "code_verifier=$codeVerifier"
)
$body = $bodyParts -join "&"

$headers = @{
    "Content-Type" = "application/x-www-form-urlencoded"
    "x-api-key"    = $keystring
}

try {
    $response = Invoke-RestMethod `
        -Uri "https://api.etsy.com/v3/public/oauth/token" `
        -Method POST `
        -Headers $headers `
        -Body $body

    Write-Host ""
    Write-Host "TOKENS GENERES AVEC SUCCES!" -ForegroundColor Green
    Write-Host "Access Token: $($response.access_token.Substring(0,20))..." -ForegroundColor Green

    # Sauvegarder tokens
    $tokensPath = Join-Path $PSScriptRoot "..\config\etsy\oauth-tokens.json"
    $tokens = @{
        access_token  = $response.access_token
        refresh_token = $response.refresh_token
        expires_in    = $response.expires_in
        generated_at  = (Get-Date -Format "o")
    } | ConvertTo-Json
    $tokens | Out-File -FilePath $tokensPath -Encoding UTF8

    # Mettre a jour .env
    $envContent = Get-Content $envPath -Raw
    $envContent = $envContent -replace "ETSYYOAUTH_ACCESS_TOKEN=.*", "ETSYYOAUTH_ACCESS_TOKEN=$($response.access_token)"
    $envContent = $envContent -replace "ETSYYOAUTH_REFRESH_TOKEN=.*", "ETSYYOAUTH_REFRESH_TOKEN=$($response.refresh_token)"
    $envContent | Set-Content $envPath -Encoding UTF8

    Write-Host ".env mis a jour!" -ForegroundColor Green
    Write-Host "Tokens sauvegardes dans config/etsy/oauth-tokens.json" -ForegroundColor Cyan

} catch {
    Write-Host "Erreur: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Details: $($_.ErrorDetails.Message)" -ForegroundColor Red
}