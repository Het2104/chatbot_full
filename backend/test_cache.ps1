# Quick FAQ Cache Testing Script
Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host " FAQ Cache Testing Script" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan

$baseUrl = "http://127.0.0.1:8000"

Write-Host "`n📋 Step 1: Checking if server is running..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/docs" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Server is running!" -ForegroundColor Green
} catch {
    Write-Host "❌ Server is not running!" -ForegroundColor Red
    Write-Host "Start the server with: python -m uvicorn app.main:app --reload" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n🤖 Step 2: Creating a test chatbot..." -ForegroundColor Yellow
$chatbotBody = @{
    name = "Test Bot $(Get-Date -Format 'HHmmss')"
    description = "Testing FAQ cache"
} | ConvertTo-Json

try {
    $chatbot = Invoke-RestMethod -Uri "$baseUrl/chatbots" -Method Post -Body $chatbotBody -ContentType "application/json"
    $chatbotId = $chatbot.id
    Write-Host "✅ Chatbot created with ID: $chatbotId" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Using existing chatbot ID: 1" -ForegroundColor Yellow
    $chatbotId = 1
}

Write-Host "`n💬 Step 3: Starting chat session..." -ForegroundColor Yellow
$sessionBody = @{
    chatbot_id = $chatbotId
} | ConvertTo-Json

$session = Invoke-RestMethod -Uri "$baseUrl/chat/start" -Method Post -Body $sessionBody -ContentType "application/json"
$sessionId = $session.session_id
Write-Host "✅ Session created with ID: $sessionId" -ForegroundColor Green

Write-Host "`n❓ Step 4: Creating test FAQ..." -ForegroundColor Yellow
$faqBody = @{
    question = "What is pricing?"
    answer = "Our pricing starts at `$10/month. We offer flexible plans."
} | ConvertTo-Json

try {
    $faq = Invoke-RestMethod -Uri "$baseUrl/chatbots/$chatbotId/faqs" -Method Post -Body $faqBody -ContentType "application/json"
    Write-Host "✅ FAQ created with ID: $($faq.id)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  FAQ might already exist, continuing..." -ForegroundColor Yellow
}

Write-Host "`n🧪 Step 5: Testing cache (First request - should be CACHE MISS)..." -ForegroundColor Yellow
$messageBody = @{
    session_id = $sessionId
    message = "What is pricing?"
} | ConvertTo-Json

$startTime = Get-Date
$response1 = Invoke-RestMethod -Uri "$baseUrl/chat/message" -Method Post -Body $messageBody -ContentType "application/json"
$time1 = ((Get-Date) - $startTime).TotalMilliseconds

Write-Host "⏱️  Response time: $([math]::Round($time1, 2))ms" -ForegroundColor Cyan
Write-Host "📝 Response: $($response1.bot_response)" -ForegroundColor White

Start-Sleep -Seconds 1

Write-Host "`n🧪 Step 6: Testing cache (Second request - should be CACHE HIT)..." -ForegroundColor Yellow
$startTime = Get-Date
$response2 = Invoke-RestMethod -Uri "$baseUrl/chat/message" -Method Post -Body $messageBody -ContentType "application/json"
$time2 = ((Get-Date) - $startTime).TotalMilliseconds

Write-Host "⏱️  Response time: $([math]::Round($time2, 2))ms" -ForegroundColor Cyan
Write-Host "📝 Response: $($response2.bot_response)" -ForegroundColor White

Write-Host "`n📊 Performance Comparison:" -ForegroundColor Cyan
Write-Host "   First request:  $([math]::Round($time1, 2))ms (Cache MISS)" -ForegroundColor Yellow
Write-Host "   Second request: $([math]::Round($time2, 2))ms (Cache HIT)" -ForegroundColor Green
if ($time1 -gt $time2) {
    $improvement = [math]::Round((($time1 - $time2) / $time1) * 100, 1)
    Write-Host "   ⚡ $improvement% faster with cache!" -ForegroundColor Green
}

Write-Host "`n🔍 Step 7: Checking Redis cache..." -ForegroundColor Yellow
try {
    $cacheKeys = docker exec chatbot-redis redis-cli KEYS "faq:*"
    if ($cacheKeys) {
        Write-Host "✅ Found $($cacheKeys.Count) FAQ cache keys:" -ForegroundColor Green
        $cacheKeys | ForEach-Object { Write-Host "   - $_" -ForegroundColor White }
    } else {
        Write-Host "⚠️  No cache keys found" -ForegroundColor Yellow
    }
} catch {
    Write-Host "⚠️  Could not check Redis (is Docker running?)" -ForegroundColor Yellow
}

Write-Host "`n==================================" -ForegroundColor Cyan
Write-Host "✅ Test Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "`n📝 Next steps:" -ForegroundColor Yellow
Write-Host "   1. Check FastAPI logs for cache HIT and cache MISS messages"
Write-Host "   2. Try querying different FAQs"
Write-Host "   3. Monitor Redis: docker exec -it chatbot-redis redis-cli MONITOR"
Write-Host ""
