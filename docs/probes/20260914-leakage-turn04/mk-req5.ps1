$ev = "C:\Users\testc\AppData\Local\Temp\opencode\gemmamonster-leakage-20260914"
New-Item -ItemType Directory -Path "$ev\test-5-real-exa-auto" -Force | Out-Null
$exaParams = [ordered]@{
  type = "object"
  properties = [ordered]@{
    query = [ordered]@{ type = "string"; description = "Natural language search query." }
    objective = [ordered]@{ type = "string"; description = "Goal for this search turn." }
    numResults = [ordered]@{ type = "integer"; description = "Number of search results to return." }
  }
  required = @("query")
  additionalProperties = $false
}
$req = [ordered]@{
  model = "gemma4"
  messages = @(
    [ordered]@{ role = "user"; content = "Please search the internet for the winner of the 2026 Eurovision Song Contest and report the winning country and song title." }
  )
  tools = @(
    [ordered]@{
      type = "function"
      function = [ordered]@{
        name = "exa_web_search_exa"
        description = "Search the web for any topic and get clean, ready-to-use content."
        parameters = $exaParams
      }
    }
  )
  tool_choice = "auto"
  max_tokens = 512
  temperature = 0
}
$req | ConvertTo-Json -Depth 12 | Set-Content "$ev\test-5-real-exa-auto\request.json"
($req.tools | ConvertTo-Json -Depth 12) | Set-Content "$ev\test-5-real-exa-auto\tools.json"
(Get-Content "$ev\server-fresh\server.stdout.log" | Measure-Object -Line).Lines | Set-Content "$ev\test-5-real-exa-auto\log-start-line.txt"
Write-Output "saved"
