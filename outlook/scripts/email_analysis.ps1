param([string]$Keyword = "")

if (-not $Keyword) {
    Write-Host "Usage: email_analysis.ps1 -Keyword <search_term>"
    exit 1
}

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$outlook = New-Object -ComObject Outlook.Application
$namespace = $outlook.GetNamespace("MAPI")

$results = @()

try {
    $folder = $namespace.GetDefaultFolder(6)
    foreach ($email in $folder.Items) {
        if ($email.Subject -like "*$Keyword*") {
            $sentTime = if ($email.SentOn) { $email.SentOn } else { $email.ReceivedTime }
            $results += [PSCustomObject]@{
                Subject = $email.Subject
                SenderName = $email.SenderName
                SenderEmail = $email.SenderEmailAddress
                To = $email.To
                CC = $email.CC
                Time = $sentTime
                Body = $email.Body
                Folder = "Inbox"
            }
        }
    }
} catch {}

try {
    $folder = $namespace.GetDefaultFolder(5)
    foreach ($email in $folder.Items) {
        if ($email.Subject -like "*$Keyword*") {
            $sentTime = if ($email.SentOn) { $email.SentOn } else { $email.ReceivedTime }
            $results += [PSCustomObject]@{
                Subject = $email.Subject
                SenderName = $email.SenderName
                SenderEmail = $email.SenderEmailAddress
                To = $email.To
                CC = $email.CC
                Time = $sentTime
                Body = $email.Body
                Folder = "SentMail"
            }
        }
    }
} catch {}

if ($results.Count -eq 0) {
    Write-Host "No emails found for keyword: $Keyword"
    exit 0
}

$results = $results | Sort-Object Time -Descending

Write-Host "=============================================="
Write-Host "Subject: $($results[0].Subject)"
Write-Host "Total matched: $($results.Count) emails"
Write-Host "=============================================="
Write-Host ""

$mainSenders = $results | Group-Object SenderName | Sort-Object Count -Descending
Write-Host "Main senders:"
foreach ($g in $mainSenders | Select-Object -First 5) {
    Write-Host "  $($g.Name): $($g.Count) emails"
}

Write-Host ""
Write-Host "Latest email:"
Write-Host "----------------------------------------------"
Write-Host "From: $($results[0].SenderName)"
Write-Host "Time: $($results[0].Time)"
Write-Host ""
$bodyLen = $results[0].Body.Length
if ($bodyLen -gt 5000) {
    Write-Host $results[0].Body.Substring(0, 5000)
} else {
    Write-Host $results[0].Body
}
Write-Host "----------------------------------------------"
Write-Host ""
Write-Host "Full chain (newest first):"
Write-Host ""

$showCount = [Math]::Min(10, $results.Count)
for ($i = 0; $i -lt $showCount; $i++) {
    $e = $results[$i]
    $bodyShort = $e.Body
    if ($bodyShort.Length -gt 400) {
        $bodyShort = $bodyShort.Substring(0, 400) + "..."
    }
    Write-Host "--- Email $($i+1) of $($results.Count) ---"
    Write-Host "From: $($e.SenderName)"
    Write-Host "Time: $($e.Time)"
    Write-Host "Subject: $($e.Subject)"
    Write-Host $bodyShort
    Write-Host ""
}
