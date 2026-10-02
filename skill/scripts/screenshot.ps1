[CmdletBinding()]
param(
    [string] $Session,

    [string] $OutputPath,

    [string] $Ref,

    [ValidateRange(1, 300)]
    [int] $TimeoutSec = 30,

    [switch] $FullPage
)

$args = @("screenshot", "--json")
if ($Session) {
    $args += "--session"
    $args += $Session
}
if ($Ref -and $FullPage) {
    throw "-Ref and -FullPage are mutually exclusive."
}
if ($Ref) {
    $args += "--ref"
    $args += $Ref
}
if ($FullPage) {
    $args += "--full-page"
    $args += "--timeout"
    $args += "$($TimeoutSec)s"
}
if ($OutputPath) {
    $args += "--out"
    $args += $OutputPath
}

try {
    $result = & bsk @args 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "bsk screenshot failed: $result"
    }
}
catch {
    throw "BrowserSkill screenshot failed: $($_.Exception.Message)"
}

try {
    $data = $result | ConvertFrom-Json
    if ($data.path) {
        $resolvedPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath(
            [string] $data.path
        )
        if (-not (Test-Path -LiteralPath $resolvedPath)) {
            throw "bsk returned a screenshot path that does not exist: $resolvedPath"
        }
        $resolvedPath
        return
    }
}
catch {
    # Not JSON or no path field — treat raw output as a path.
}

# Fallback: raw output may be a bare path.
$rawPath = $result.Trim()
if ($rawPath -and (Test-Path -LiteralPath $rawPath)) {
    $rawPath
    return
}

throw "bsk screenshot returned an unexpected response: $result"
