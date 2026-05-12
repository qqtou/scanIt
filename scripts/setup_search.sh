#!/bin/bash
# ScanIt 搜索引擎配置脚本
# 用途：自动检测并配置搜索引擎 API Key

set -e

echo "================================================"
echo "  ScanIt 搜索引擎配置向导"
echo "================================================"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 打印成功
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

# 打印错误
print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# 打印警告
print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# 检测环境
echo ">>> 检测运行环境..."

if command_exists docker; then
    print_success "Docker 已安装: $(docker --version)"
else
    print_error "Docker 未安装"
    echo "  请安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
    print_success "Docker Compose 已安装"
else
    print_error "Docker Compose 未安装"
    exit 1
fi

echo ""

# 检查 .env 文件
echo ">>> 检查配置文件..."

if [ -f ".env" ]; then
    print_success ".env 文件已存在"
else
    print_warning ".env 文件不存在，从模板创建..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success "已创建 .env 文件"
    else
        print_error ".env.example 不存在"
        exit 1
    fi
fi

echo ""

# 检测搜索引擎配置
echo ">>> 检测搜索引擎配置..."

# 加载 .env
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

has_search_provider=false

# 检查博查 AI
if [ -n "$BOCHA_API_KEY" ]; then
    print_success "博查 AI 已配置: BOCHA_API_KEY=${BOCHA_API_KEY:0:10}..."
    has_search_provider=true
fi

# 检查 Google
if [ -n "$GOOGLE_API_KEY" ] && [ -n "$GOOGLE_SEARCH_ENGINE_ID" ]; then
    print_success "Google Custom Search 已配置"
    has_search_provider=true
fi

# 检查 Bing
if [ -n "$BING_API_KEY" ]; then
    print_success "Bing Web Search 已配置"
    has_search_provider=true
fi

if [ "$has_search_provider" = false ]; then
    print_error "未配置任何搜索引擎 API Key"
    echo ""
    echo "请配置以下任一搜索引擎："
    echo ""
    echo "  [推荐] 博查 AI（国内部署，数据不出海）"
    echo "    申请地址: https://open.bochaai.com"
    echo "    配置方式:"
    echo "      SEARCH_PROVIDER=bocha"
    echo "      BOCHA_API_KEY=your_key"
    echo ""
    echo "  [备选] Google Custom Search（免费 100 次/天）"
    echo "    申请地址: https://console.cloud.google.com"
    echo "    配置方式:"
    echo "      SEARCH_PROVIDER=google"
    echo "      GOOGLE_API_KEY=your_key"
    echo "      GOOGLE_SEARCH_ENGINE_ID=your_cx"
    echo ""
    echo "  [备选] Bing Web Search（免费 1000 次/月）"
    echo "    申请地址: https://portal.azure.com"
    echo "    配置方式:"
    echo "      SEARCH_PROVIDER=bing"
    echo "      BING_API_KEY=your_key"
    echo ""
    exit 1
fi

echo ""

# 检查 JWT 密钥
echo ">>> 检查安全配置..."

if [ -n "$JWT_SECRET_KEY" ] && [ ${#JWT_SECRET_KEY} -ge 32 ]; then
    print_success "JWT_SECRET_KEY 已配置（长度: ${#JWT_SECRET_KEY}）"
else
    print_warning "JWT_SECRET_KEY 未配置或过短"
    echo "  正在生成随机密钥..."
    
    NEW_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)
    
    # 更新 .env
    if grep -q "^JWT_SECRET_KEY=" .env; then
        sed -i.bak "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW_KEY|" .env
    else
        echo "JWT_SECRET_KEY=$NEW_KEY" >> .env
    fi
    
    print_success "已生成 JWT_SECRET_KEY: ${NEW_KEY:0:10}..."
fi

echo ""

# 检查爬虫模式
echo ">>> 检查爬虫配置..."

if [ "$SEARCH_SCRAPE_ENABLED" = "true" ]; then
    print_warning "爬虫模式已启用（不推荐）"
    echo "  爬虫模式存在反爬风险，建议使用官方 API"
else
    print_success "爬虫模式已禁用（推荐）"
fi

echo ""

# 总结
echo "================================================"
echo "  配置检查完成"
echo "================================================"
echo ""

if [ "$has_search_provider" = true ]; then
    print_success "搜索引擎配置正常"
    print_success "安全配置正常"
    echo ""
    echo "后续步骤："
    echo "  1. 启动服务: docker-compose up -d"
    echo "  2. 初始化数据库: docker-compose exec backend alembic upgrade head"
    echo "  3. 访问应用: http://localhost:8000/docs"
    echo ""
else
    print_error "请先配置搜索引擎 API Key"
    exit 1
fi
