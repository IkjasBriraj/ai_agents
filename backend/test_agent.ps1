# PowerShell Test Script for Multi-Agent System

Write-Host "Testing Multi-Agent System..." -ForegroundColor Cyan

# Test 1: Simple HTML page creation
Write-Host "`n=== Test 1: Create Simple HTML Page ===" -ForegroundColor Yellow

$body = @{
    prompt = "Create a simple HTML page called hello.html with a greeting"
    stream = $false
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/chat" `
        -Method Post `
        -ContentType "application/json" `
        -Body $body
    
    Write-Host "Success!" -ForegroundColor Green
    Write-Host "Response:" -ForegroundColor Cyan
    Write-Host $response.response
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

# Test 2: Check if file was created
Write-Host "`n=== Checking if file was created ===" -ForegroundColor Yellow
$websiteDir = "D:\learning\code\website"
if (Test-Path $websiteDir) {
    $files = Get-ChildItem $websiteDir
    Write-Host "Files in website directory:" -ForegroundColor Cyan
    $files | ForEach-Object { Write-Host "  - $($_.Name)" }
} else {
    Write-Host "Website directory not found!" -ForegroundColor Red
}

# Test 3: Get available agents
Write-Host "`n=== Test 2: Get Available Agents ===" -ForegroundColor Yellow

try {
    $agents = Invoke-RestMethod -Uri "http://localhost:8000/api/multi-agent/agents/available" `
        -Method Get
    
    Write-Host "Available Agents:" -ForegroundColor Green
    $agents.agents | ForEach-Object {
        Write-Host "  - $($_.name) ($($_.type))" -ForegroundColor Cyan
    }
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
}

Write-Host "`n=== Tests Complete ===" -ForegroundColor Green

# Made with Bob
