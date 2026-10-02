#!/usr/bin/env bash
# ============================================================
# ZenX Bridge Skill 一键安装脚本（Linux / macOS）
# 支持 CodeBuddy / WorkBuddy 环境
#
# 用法:
#   ./install.sh [选项]
#
# 选项:
#   -b, --branch <name>    安装指定分支或标签 (默认: main)
#   -t, --target-path <path>  自定义安装路径 (默认: 自动检测)
#   -f, --force            强制覆盖已有安装
#   -h, --help             显示帮助信息
#   -v, --verbose          显示详细输出
#   --dry-run              仅模拟安装，不实际执行
#
# 示例:
#   ./install.sh                           # 默认安装 main 分支
#   ./install.sh -b v1.0.0                 # 安装 v1.0.0 版本
#   ./install.sh -f                        # 强制覆盖
#   ./install.sh -t ~/my-skills/bsk        # 自定义路径
#   ./install.sh --dry-run                 # 模拟运行
#
# 版本: 1.1.0
# 作者: ZenX Bridge Skill Team
# ============================================================

set -euo pipefail

# ============================================================
# 颜色定义
# ============================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# ============================================================
# 全局变量
# ============================================================
REPO_URL="https://github.com/916938/zenx-bridge-skill.git"
BRANCH="main"
TARGET_PATH=""
FORCE=false
VERBOSE=false
DRY_RUN=false
TEMP_DIR=""
SCRIPT_VERSION="1.1.0"

# ============================================================
# 辅助函数
# ============================================================

log_info() {
    echo -e "${GREEN}[INFO]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*"
    fi
}

show_header() {
    echo -e "${CYAN}========================================${NC}"
    echo -e "  ZenX Bridge Skill 安装向导"
    echo -e "  版本: ${SCRIPT_VERSION} | 平台: $(uname -s)"
    echo -e "${CYAN}========================================${NC}\n"
}

show_help() {
    cat << EOF
ZenX Bridge Skill 安装脚本 - Linux/macOS 版本

用法:
    $0 [选项]

选项:
    -b, --branch <name>       安装指定分支或标签 (默认: ${BRANCH})
    -t, --target-path <path>  自定义安装路径 (默认: 自动检测 Agent 目录)
    -f, --force               强制覆盖已有安装
    -h, --help                显示此帮助信息
    -v, --verbose             显示详细调试输出
    --dry-run                 仅模拟安装，不实际执行任何操作

示例:
    # 基本安装（使用自动检测的路径）
    $0

    # 安装特定版本
    $0 -b v1.0.0

    # 强制覆盖已存在的安装
    $0 -f

    # 安装到自定义位置
    $0 -t ~/my-custom-skills/zenx-bridge-skill

    # 模拟运行（查看将执行的操作但不实际执行）
    $0 --dry-run -v

支持的 Agent 环境:
• CodeBuddy  (~/.codebuddy/skills/)
• Claude Code  (~/.claude/skills/ 或 ~/.claude/commands/)
• WorkBuddy  (~/.workbuddy/skills/)
• Codex      (~/.codex/skills/)
EOF
}

cleanup() {
    log_debug "清理临时目录..."
    if [[ -n "$TEMP_DIR" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
        log_debug "临时目录已删除: $TEMP_DIR"
    fi
}

# 信号处理
trap cleanup EXIT INT TERM

# ============================================================
# 检测函数
# ============================================================

check_prerequisites() {
    log_info "检查前置条件..."

    # 检查 Git
    if ! command -v git &> /dev/null; then
        log_error "未找到 Git。请先安装 Git:"
        case "$(uname -s)" in
            Linux*)
                echo "  Ubuntu/Debian: sudo apt update && sudo apt install -y git"
                echo "  Fedora/RHEL:   sudo dnf install -y git"
                echo "  Arch Linux:    sudo pacman -S git"
                ;;
            Darwin*)
                echo "  macOS: brew install git"
                ;;
            *)
                echo "  请访问 https://git-scm.com/downloads 获取安装包"
                ;;
        esac
        exit 1
    fi
    local git_version
    git_version=$(git --version)
    log_info "  ✓ Git 已安装: $git_version"

    # 检查 Python3（用于验证）
    if ! command -v python3 &> /dev/null; then
        log_warn "⚠ 未找到 Python3。建议安装以使用 doctor.py 等工具:"
        case "$(uname -s)" in
            Linux*)  echo "  sudo apt install -y python3" ;;
            Darwin*) echo "  brew install python3" ;;
        esac
        log_warn "继续安装（Python3 为可选依赖）..."
    else
        local py_version
        py_version=$(python3 --version)
        log_info "  ✓ Python3 可用: $py_version"
    fi

    # 检查网络连接（可选，通过后续 git clone 验证）
    log_info "  ✓ 前置条件检查通过\n"
}

detect_target_path() {
    if [[ -n "$TARGET_PATH" ]]; then
        log_info "使用指定的目标路径: $TARGET_PATH"
        return
    fi

    log_debug "正在检测 Agent skills 目录..."

    # 检测顺序：CodeBuddy > Claude Code > WorkBuddy > Codex
    local possible_paths=(
        "$HOME/.codebuddy/skills/zenx-bridge-skill"
        "$HOME/.claude/skills/zenx-bridge-skill"
        "$HOME/.claude/commands/zenx-bridge-skill"
        "$HOME/.workbuddy/skills/zenx-bridge-skill"
        "$HOME/.codex/skills/zenx-bridge-skill"
    )

    for path in "${possible_paths[@]}"; do
        local parent_dir
        parent_dir=$(dirname "$path")
        if [[ -d "$parent_dir" ]]; then
            TARGET_PATH="$path"
            log_info "检测到 Agent 环境: $parent_dir"
            return
        fi
    done

    # 默认使用 .codebuddy/skills
    TARGET_PATH="$HOME/.codebuddy/skills/zenx-bridge-skill"
    log_info "使用默认路径: $TARGET_PATH"
}

check_existing_installation() {
    if [[ -d "$TARGET_PATH" ]]; then
        if [[ "$FORCE" == "true" ]]; then
            log_warn "检测到已有安装，将使用 --force 覆盖"

            # 备份旧版本
            local backup_path="${TARGET_PATH}.backup-$(date +%Y%m%d-%H%M%S)"
            if [[ "$DRY_RUN" != "true" ]]; then
                cp -r "$TARGET_PATH" "$backup_path" 2>/dev/null || true
                log_info "旧版本备份至: $backup_path"
            else
                log_info "[DRY RUN] 将备份旧版本到: $backup_path"
            fi
        else
            log_error "目标目录已存在: $TARGET_PATH"
            echo ""
            echo "解决方案:"
            echo "  1. 使用 --force 参数覆盖现有安装:  \$0 -f"
            echo "  2. 使用 --target-path 指定其他路径: \$0 -t ~/other-path"
            echo "  3. 手动删除现有目录后重新运行"
            exit 1
        fi
    fi
}

# ============================================================
# 安装函数
# ============================================================

clone_repository() {
    TEMP_DIR=$(mktemp -d -t bsk-install-XXXXXX)

    log_info "正在从 GitHub 仓库下载..."
    log_debug "仓库地址: $REPO_URL"
    log_debug "分支/标签: $BRANCH"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] 将执行: git clone --branch $BRANCH --depth 1 $REPO_URL $TEMP_DIR"
        return
    fi

    # 使用浅克隆加速下载
    if ! git clone --branch "$BRANCH" --depth 1 --single-branch "$REPO_URL" "$TEMP_DIR" 2>&1 | while IFS= read -r line; do
        if [[ "$line" == *"Cloning"* || "$line" == *"Receiving"* || "$line" == *"Resolving"* ]]; then
            log_debug "  $line"
        fi
    done; then
        log_error "Git clone 失败。请检查:"
        echo "  1. 网络连接是否正常"
        echo "  2. 仓库地址是否正确: $REPO_URL"
        echo "  3. 分支名称是否正确: $BRANCH"
        exit 1
    fi

    log_info "✓ 仓库下载成功"

    # 验证 skill 目录存在
    local source_skill_dir="$TEMP_DIR/skill"
    if [[ ! -d "$source_skill_dir" ]]; then
        log_error "下载的仓库结构异常：缺少 'skill' 目录"
        exit 1
    fi
}

install_files() {
    local target_parent_dir
    target_parent_dir=$(dirname "$TARGET_PATH")

    log_info "正在复制文件到目标位置..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "[DRY RUN] 将创建目录: $target_parent_dir"
        log_info "[DRY RUN] 将复制: $TEMP_DIR/skill/* → $TARGET_PATH"
        return
    fi

    # 创建父目录
    mkdir -p "$target_parent_dir" 2>/dev/null || true

    # 删除旧版本（如果使用 force）
    if [[ "$FORCE" == "true" && -d "$TARGET_PATH" ]]; then
        rm -rf "$TARGET_PATH"
    fi

    # 复制文件
    cp -r "$TEMP_DIR/skill/." "$TARGET_PATH"

    log_info "✓ 文件复制完成"
}

verify_installation() {
    log_info "正在验证安装..."

    local required_items=("SKILL.md" "scripts" "references")
    local all_passed=true
    local installed_items=()

    for item in "${required_items[@]}"; do
        local item_path="$TARGET_PATH/$item"
        if [[ -e "$item_path" ]]; then
            installed_items+=("$item")
            log_info "  ✓ $item"
        else
            log_error "  ✗ 缺少必要项: $item"
            all_passed=false
        fi
    done

    # 统计文件数量
    local file_count dir_count
    file_count=$(find "$TARGET_PATH" -type f 2>/dev/null | wc -l | tr -d ' ')
    dir_count=$(find "$TARGET_PATH" -type d 2>/dev/null | wc -l | tr -d ' ')

    if [[ "$all_passed" != "true" ]]; then
        log_error "安装验证失败：缺少必要文件或目录"
        exit 1
    fi

    show_success_results "$file_count" "$dir_count" "${installed_items[@]}"
}

show_success_results() {
    local file_count=$1
    local dir_count=$2
    shift 2
    local installed_items=("$@")

    echo ""
    echo -e "${CYAN}$( printf '=%.0s' {1..50} )${NC}"
    echo -e "${GREEN}${BOLD}✓ ZenX Bridge Skill 安装成功！${NC}"
    echo -e "${CYAN}$( printf '=%.0s' {1..50} )${NC}\n"

    # 显示安装详情
    echo -e "${YELLOW}📋 安装详情:${NC}"
    echo -e "  安装路径:"
    echo -e "    ${CYAN}$TARGET_PATH${NC}"
    echo ""
    echo -e "  文件统计:"
    echo -e "    - 目录数: $dir_count"
    echo -e "    - 文件数: $file_count"
    echo ""
    echo -e "  包含组件:"
    for item in "${installed_items[@]}"; do
        echo -e "    ${GREEN}✓${NC} $item"
    done
    echo ""

    # 后续步骤
    echo -e "${YELLOW}🔧 后续步骤:${NC}"
    echo ""
    echo -e "  ${BOLD}1️⃣  重启 Agent${NC}"
    echo -e "     关闭并重新打开 CodeBuddy / WorkBuddy 以加载新 skill"
    echo ""
    echo -e "  ${BOLD}2️⃣  运行自检（推荐）${NC}"
    echo -e "     在终端中执行:"
    echo -e ""
    echo -e "     ${CYAN}python3 \"${TARGET_PATH}/scripts/doctor.py\" --wait-connected 20${NC}"
    echo ""
    echo -e "  ${BOLD}3️⃣  测试功能${NC}"
    echo -e "     在 CodeBuddy / WorkBuddy 对话框中输入:"
    echo -e ""
    echo -e "     ${CYAN}使用 \$zenx-bridge-skill 查看当前浏览器状态${NC}"
    echo ""

    # 常用命令速查
    echo -e "${YELLOW}⚡ 常用命令速查:${NC}"
    echo ""
    echo -e "  ${BOLD}• 环境自检:${NC}"
    echo -e "    python3 \"${TARGET_PATH}/scripts/doctor.py\""
    echo ""
    echo -e "  ${BOLD}• 页面快照（精简）:${NC}"
    echo -e "    python3 \"${TARGET_PATH}/scripts/snapshot.py\" --session demo --auto"
    echo ""
    echo -e "  ${BOLD}• 页面快照（完整）:${NC}"
    echo -e "    python3 \"${TARGET_PATH}/scripts/snapshot.py\" --session demo --mode file"
    echo ""
    echo -e "  ${BOLD}• 截图:${NC}"
    echo -e "    python3 \"${TARGET_PATH}/scripts/screenshot.py\" --session demo"
    echo ""
    echo -e "  ${BOLD}• 等待页面加载:${NC}"
    echo -e "    python3 \"${TARGET_PATH}/scripts/wait_for.py\" --session demo \\"
    echo -e "      --url-contains \"example.com\" --timeout 10"
    echo ""
    echo -e "  ${BOLD}• 运行单元测试:${NC}"
    local tests_dir
    tests_dir=$(dirname "$TARGET_PATH")/tests
    echo -e "    python3 -m unittest discover -s \"$tests_dir\" -v"
    echo ""

    # 卸载说明
    echo -e "${YELLOW}🗑️  卸载说明（如果需要）:${NC}"
    echo -e "  直接删除安装目录即可:"
    echo -e "  ${CYAN}rm -rf \"${TARGET_PATH}\"${NC}"
    echo ""
}

# ============================================================
# 主函数
# ============================================================

main() {
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--branch)
                BRANCH="$2"
                shift 2
                ;;
            -t|--target-path)
                TARGET_PATH="$2"
                shift 2
                ;;
            -f|--force)
                FORCE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                VERBOSE=true  # dry-run 自动启用 verbose
                shift
                ;;
            *)
                log_error "未知参数: $1"
                echo "使用 -h 或 --help 查看帮助信息"
                exit 1
                ;;
        esac
    done

    # 显示头部信息
    show_header

    # 如果是 dry-run 模式
    if [[ "$DRY_RUN" == "true" ]]; then
        log_warn "*** DRY RUN 模式 - 不会执行实际的安装操作 ***\n"
    fi

    # 执行安装流程
    check_prerequisites
    detect_target_path
    check_existing_installation
    clone_repository
    install_files
    verify_installation

    log_info "安装完成！"
}

# ============================================================
# 入口点
# ============================================================

main "$@"
