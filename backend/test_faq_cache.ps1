# FAQ Cache Testing Script - Simple Version
Write-Host "`nFAQ Cache Testing Script" -ForegroundColor Cyan
Write-Host "========================`n" -ForegroundColor Cyan

$baseUrl = "http://127.0.0.1:8000"

# Step 1: Check server
Write-Host "Step 1: Checking if server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "$baseUrl/chatbots" -Method Get -TimeoutSec 5
    Write-Host "Server is running!" -ForegroundColor Green
    Write-Host "Found $($response.Count) existing chatbots`n" -ForegroundColor White
} catch {
    Write-Host "ERROR: Server is not running!" -ForegroundColor Red
    Write-Host "Start it with: python -m uvicorn app.main:app --reload`n" -ForegroundColor Yellow
    exit 1
}

# Use existing chatbot or create new one
if ($response.Count -gt 0) {
    $chatbotId = $response[0].id
    Write-Host "Using existing chatbot ID: $chatbotId`n" -ForegroundColor Green
} else {
    Write-Host "Step 2: Creating a test chatbot..." -ForegroundColor Yellow
    $chatbotBody = @{
        name = "Test Bot"
        description = "Testing FAQ cache"
    } | ConvertTo-Json
    
    $chatbot = Invoke-RestMethod -Uri "$baseUrl/chatbots" -Method Post -Body $chatbotBody -ContentType "application/json"
    $chatbotId = $chatbot.id
    Write-Host "Chatbot created with ID: $chatbotId`n" -ForegroundColor Green
}

# Step 3: Start chat session
Write-Host "Step 3: Starting chat session..." -ForegroundColor Yellow
$sessionBody = @{
    chatbot_id = $chatbotId
} | ConvertTo-Json

$session = Invoke-RestMethod -Uri "$baseUrl/chat/start" -Method Post -Body $sessionBody -ContentType "application/json"
$sessionId = $session.session_id
Write-Host "Session created with ID: $sessionId`n" -ForegroundColor Green

# Step 4: Create FAQ
Write-Host "Step 4: Creating test FAQ..." -ForegroundColor Yellow
$faqBody = @{
    question = "What is pricing?"
    answer = "Our pricing starts at dollar 10/month. We offer flexible plans."
} | ConvertTo-Json

try {
    $faq = Invoke-RestMethod -Uri "$baseUrl/chatbots/$chatbotId/faqs" -Method Post -Body $faqBody -ContentType "application/json"
    Write-Host "FAQ created with ID: $($faq.id)`n" -ForegroundColor Green
} catch {
    Write-Host "FAQ might already exist, continuing...`n" -ForegroundColor Yellow
}

# Step 5: First request (Cache MISS)
Write-Host "Step 5: Testing cache - First request (should be CACHE MISS)..." -ForegroundColor Yellow
$messageBody = @{
    session_id = $sessionId
    message = "What is pricing?"
} | ConvertTo-Json

$startTime = Get-Date
$response1 = Invoke-RestMethod -Uri "$baseUrl/chat/message" -Method Post -Body $messageBody -ContentType "application/json"
$time1 = ((Get-Date) - $startTime).TotalMilliseconds

Write-Host "Response time: $([math]::Round($time1, 2))ms" -ForegroundColor Cyan
Write-Host "Response: $($response1.bot_response)`n" -ForegroundColor White

# Wait a moment
Start-Sleep -Seconds 1

# Step 6: Second request (Cache HIT)
Write-Host "Step 6: Testing cache - Second request (should be CACHE HIT)..." -ForegroundColor Yellow
$startTime = Get-Date
$response2 = Invoke-RestMethod -Uri "$baseUrl/chat/message" -Method Post -Body $messageBody -ContentType "application/json"
$time2 = ((Get-Date) - $startTime).TotalMilliseconds

Write-Host "Response time: $([math]::Round($time2, 2))ms" -ForegroundColor Cyan
Write-Host "Response: $($response2.bot_response)`n" -ForegroundColor White

# Performance comparison
Write-Host "Performance Comparison:" -ForegroundColor Cyan
Write-Host "  First request:  $([math]::Round($time1, 2))ms (Cache MISS)" -ForegroundColor Yellow
Write-Host "  Second request: $([math]::Round($time2, 2))ms (Cache HIT)" -ForegroundColor Green
if ($time1 -gt $time2) {
    $improvement = [math]::Round((($time1 - $time2) / $time1) * 100, 1)
    Write-Host "  Speed improvement: $improvement% faster!`n" -ForegroundColor Green
}

# Step 7: Check Redis
Write-Host "Step 7: Checking Redis cache..." -ForegroundColor Yellow
try {
    $cacheKeys = docker exec chatbot-redis redis-cli KEYS "faq:*"
    if ($cacheKeys) {
        Write-Host "Found cache keys in Redis:" -ForegroundColor Green
        $cacheKeys | ForEach-Object { Write-Host "  - $_" -ForegroundColor White }
    } else {
        Write-Host "No cache keys found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Could not check Redis (is Docker running?)" -ForegroundColor Yellow
}

Write-Host "`n================================" -ForegroundColor Cyan
Write-Host "Test Complete!" -ForegroundColor Green
Write-Host "================================" -ForegroundColor Cyan
Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Check FastAPI logs for cache HIT and cache MISS messages"
Write-Host "  2. Try querying different FAQs"
Write-Host "  3. Monitor Redis: docker exec -it chatbot-redis redis-cli MONITOR`n"
