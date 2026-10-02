<#
.SYNOPSIS
    ZenX Bridge Skill 一键安装脚本（CodeBuddy / WorkBuddy 环境）
.DESCRIPTION
    从 GitHub 仓库自动下载并安装 ZenX Bridge Skill skill 到 CodeBuddy 或 WorkBuddy 的 skills 目录。
    支持自定义分支、强制覆盖、多环境检测。
.PARAMETER RepoUrl
    GitHub 仓库地址（默认: https://github.com/916938/zenx-bridge-skill.git）
.PARAMETER Branch
    要安装的分支或标签（默认: main）
.PARAMETER TargetPath
    自定义安装路径（默认: 自动检测）
.PARAMETER Force
    强制覆盖已有安装
.EXAMPLE
    .\install.ps1
    使用默认设置安装最新版本
.EXAMPLE
    .\install.ps1 -Branch v1.0.0 -Force
    安装 v1.0.0 版本并覆盖已有文件
.EXAMPLE
    .\install.ps1 -TargetPath "C:\MySkills\zenx-bridge-skill"
    安装到自定义路径
.NOTES
    文件名: install.ps1
    作者: ZenX Bridge Skill Team
    版本: 1.1.0
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$RepoUrl = "https://github.com/916938/zenx-bridge-skill.git",

    [Parameter(Mandatory = $false)]
    [string]$Branch = "main",

    [Parameter(Mandatory = $false)]
    [string]$TargetPath,

    [Parameter(Mandatory = $false)]
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# ============================================================
# 辅助函数
# ============================================================

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Test-GitAvailable {
    try {
        $null = git --version 2>&1
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Get-InstallPaths {
    # 检测常见的 Agent skills 路径
    @(
        @{
            Name = "CodeBuddy (User Profile)"
            Path = "$env:USERPROFILE\.codebuddy\skills\zenx-bridge-skill"
        },
        @{
            Name = "WorkBuddy (User Profile)"
            Path = "$env:USERPROFILE\.workbuddy\skills\zenx-bridge-skill"
        },
        @{
            Name = "Claude Code (User Profile)"
            Path = "$env:USERPROFILE\.claude\skills\zenx-bridge-skill"
        },
        @{
            Name = "Claude Code (Commands)"
            Path = "$env:USERPROFILE\.claude\commands\zenx-bridge-skill"
        },
        @{
            Name = "Codex (User Profile)"
            Path = "$env:USERPROFILE\.codex\skills\zenx-bridge-skill"
        },
        @{
            Name = "CodeBuddy (AppData)"
            Path = "$env:APPDATA\CodeBuddy\skills\zenx-bridge-skill"
        }
    )
}

function Resolve-TargetPath {
    if ($TargetPath) {
        return $TargetPath
    }

    # 尝试自动检测已存在的 Agent 目录
    $paths = Get-InstallPaths
    foreach ($entry in $paths) {
        $parentDir = Split-Path $entry.Path -Parent
        if (Test-Path $parentDir) {
            Write-Verbose "检测到 Agent 环境: $($entry.Name)"
            return $entry.Path
        }
    }

    # 默认使用 .codebuddy/skills
    return "$env:USERPROFILE\.codebuddy\skills\zenx-bridge-skill"
}

function Remove-TempDirectory {
    param([string]$Path)
    if (Test-Path $Path) {
        Remove-Item -Recurse -Force $Path -ErrorAction SilentlyContinue
    }
}

# ============================================================
# 主安装流程
# ============================================================

Write-ColorOutput "`n========================================" Cyan
Write-ColorOutput "  ZenX Bridge Skill 安装向导" White
Write-ColorOutput "  版本: 1.1.0 | 平台: Windows" Gray
Write-ColorOutput "========================================`n" Cyan

try {
    # 步骤 1：前置检查
    Write-ColorOutput "📋 前置检查..." Yellow
    
    # 检查 Git
    if (-not (Test-GitAvailable)) {
        throw "未找到 Git。请先安装 Git: https://git-scm.com/download/win"
    }
    Write-ColorOutput "   ✅ Git 已安装" Green

    # 检查网络连接（可选）
    # 这里跳过网络检查，让 git clone 失败时自然报错

    # 步骤 2：解析目标路径
    $resolvedTargetPath = Resolve-TargetPath
    $targetParentDir = Split-Path $resolvedTargetPath -Parent

    Write-ColorOutput "`n📂 目标路径:" Yellow
    Write-ColorOutput "   $resolvedTargetPath" White

    # 步骤 3：检查是否已安装
    if ((Test-Path $resolvedTargetPath)) {
        if ($Force) {
            Write-ColorOutput "   ⚠️  检测到已有安装，将使用 -Force 覆盖" Red
            # 备份旧版本（可选）
            $backupPath = "$resolvedTargetPath.backup-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Copy-Item $resolvedTargetPath $backupPath -Recurse -Force
            Write-ColorOutput "   📦 旧版本备份至: $backupPath" Gray
        } else {
            Write-ColorOutput "`n❌ 目标目录已存在。如需覆盖请使用 -Force 参数。" Red
            Write-ColorOutput "   示例: .\install.ps1 -Force`n" Yellow
            exit 1
        }
    }

    # 步骤 4：克隆仓库
    $tempDir = Join-Path $env:TEMP "bsk-install-$([guid]::NewGuid().ToString('N'))"
    
    Write-ColorOutput "`n📥 正在从 GitHub 仓库下载..." Yellow
    Write-ColorOutput "   仓库: $RepoUrl" Gray
    Write-ColorOutput "   分支: $Branch" Gray
    Write-ColorOutput ""

    # 使用浅克隆加速下载（--depth 1）
    & git clone --branch $Branch --depth 1 --single-branch $RepoUrl $tempDir 2>&1 | ForEach-Object {
        if ($_ -match "Cloning|Receiving|Resolving") {
            Write-Host "   $_" -ForegroundColor DarkGray
        }
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Git clone 失败。请检查：1) 网络连接 2) 仓库地址 3) 分支名称是否正确"
    }

    Write-ColorOutput "   ✅ 仓库下载成功" Green

    # 验证 skill 目录存在
    $sourceSkillDir = Join-Path $tempDir "skill"
    if (-not (Test-Path $sourceSkillDir)) {
        throw "下载的仓库结构异常：缺少 'skill' 目录"
    }

    # 步骤 5：复制文件到目标位置
    Write-ColorOutput "`n📦 正在复制文件..." Yellow

    # 创建目标父目录（如果不存在）
    New-Item -ItemType Directory -Path $targetParentDir -Force -ErrorAction SilentlyContinue | Out-Null

    # 删除旧版本（如果使用 Force）
    if ($Force -and (Test-Path $resolvedTargetPath)) {
        Remove-Item $resolvedTargetPath -Recurse -Force
    }

    # 复制 skill 内容
    Copy-Item "$sourceSkillDir\*" -Destination $resolvedTargetPath -Recurse -Force

    Write-ColorOutput "   ✅ 文件复制完成" Green

    # 步骤 6：验证安装
    Write-ColorOutput "`n🔍 正在验证安装..." Yellow

    $requiredFilesAndDirs = @("SKILL.md", "scripts", "references")
    $validationPassed = $true
    $installedItems = @()

    foreach ($item in $requiredFilesAndDirs) {
        $itemPath = Join-Path $resolvedTargetPath $item
        if (Test-Path $itemPath) {
            $installedItems += $item
            Write-ColorOutput "   ✅ $item" Green
        } else {
            Write-ColorOutput "   ❌ 缺少必要项: $item" Red
            $validationPassed = $false
        }
    }

    # 统计文件数量
    $fileCount = (Get-ChildItem $resolvedTargetPath -File -Recurse).Count
    $dirCount = (Get-ChildItem $resolvedTargetPath -Directory -Recurse).Count

    if (-not $validationPassed) {
        throw "安装验证失败：缺少必要文件或目录。请尝试重新运行安装脚本。"
    }

    # 步骤 7：显示安装结果
    Write-ColorOutput "`n$( '=' * 50 )" Cyan
    Write-ColorOutput "✅ ZenX Bridge Skill 安装成功！" Green
    Write-ColorOutput "$( '=' * 50 )`n" Cyan

    # 显示安装详情
    Write-ColorOutput "📋 安装详情:" Yellow
    Write-ColorOutput "   安装路径:" White
    Write-ColorOutput "      $resolvedTargetPath" Cyan
    Write-ColorOutput ""
    Write-ColorOutput "   文件统计:" White
    Write-ColorOutput "      - 目录数: $dirCount" Gray
    Write-ColorOutput "      - 文件数: $fileCount" Gray
    Write-ColorOutput ""
    Write-ColorOutput "   包含组件:" White
    foreach ($item in $installedItems) {
        Write-ColorOutput "      ✓ $item" DarkGreen
    }

    # 显示后续步骤
    Write-ColorOutput ""
    Write-ColorOutput "🔧 后续步骤:" Yellow
    Write-ColorOutput ""
    Write-ColorOutput "  1️⃣  重启 Agent" White
    Write-ColorOutput "     关闭并重新打开 CodeBuddy / WorkBuddy，以加载新安装的 skill。" Gray
    Write-ColorOutput ""
    Write-ColorOutput "  2️⃣  运行自检（推荐）" White
    Write-ColorOutput "     在 PowerShell 中执行以下命令检查环境：" Gray
    Write-ColorOutput ""
    Write-ColorOutput '     py -3 "{0}\scripts\doctor.py" --wait-connected 20' -f $resolvedTargetPath Cyan
    Write-ColorOutput ""
    Write-ColorOutput "  3️⃣  测试功能" White
    Write-ColorOutput "     在 CodeBuddy / WorkBuddy 对话框中输入：" Gray
    Write-ColorOutput ""
    Write-ColorOutput '     使用 $zenx-bridge-skill 查看当前浏览器状态' -f $resolvedTargetPath Cyan
    Write-ColorOutput ""

    # 显示快速命令参考
    Write-ColorOutput "⚡ 常用命令速查:" Yellow
    Write-ColorOutput ""

    $commands = @(
        @{Cmd = 'py -3 "{0}\scripts\doctor.py"' -f $resolvedTargetPath; Desc = "环境自检"},
        @{Cmd = 'py -3 "{0}\scripts\snapshot.py" --session demo --auto' -f $resolvedTargetPath; Desc = "页面快照"},
        @{Cmd = 'py -3 "{0}\scripts\screenshot.py" --session demo' -f $resolvedTargetPath; Desc = "截图"},
        @{Cmd = 'py -3 -m unittest discover -s {0}\..\tests -v' -f (Split-Path $resolvedTargetPath); Desc = "运行测试"}
    )

    foreach ($entry in $commands) {
        Write-ColorOutput "   • $($entry.Desc):" White
        Write-ColorOutput "      $($entry.Cmd)" Cyan
        Write-ColorOutput ""
    }

    # 显示卸载信息
    Write-ColorOutput "🗑️  卸载说明（如果需要）:" Yellow
    Write-ColorOutput "     直接删除安装目录即可：" Gray
    Write-ColorOutput "     Remove-Item -Recurse -Force `"$resolvedTargetPath""" White
    Write-ColorOutput ""

}
catch {
    Write-ColorOutput "`n❌ 安装失败!" Red
    Write-ColorOutput "   错误信息: $_" White
    Write-ColorOutput ""
    Write-ColorOutput "   故障排除建议:" Yellow
    Write-ColorOutput "   1. 检查网络连接是否正常" Gray
    Write-ColorOutput "   2. 确认 Git 已正确安装并在 PATH 中" Gray
    Write-ColorOutput "   3. 验证仓库地址和分支名称是否正确" Gray
    Write-ColorOutput "   4. 检查目标目录是否有写入权限" Gray
    Write-ColorOutput "   5. 如果问题持续，请查看 GitHub Issues:" Gray
    Write-ColorOutput "      https://github.com/916938/zenx-bridge-skill/issues" Cyan
    Write-ColorOutput ""
    
    exit 1
}
finally {
    # 清理临时文件
    if (Test-Path $tempDir) {
        Remove-TempDirectory $tempDir
    }
}
