#!/bin/bash

# اسکریپت نصب و راه‌اندازی سلف بات تلگرام
# این اسکریپت پیش‌نیازها را بررسی کرده و پروژه را نصب می‌کند

# تنظیم رنگ‌ها برای خروجی
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# چاپ banner
echo -e "${GREEN}"
echo -e "████████╗███████╗██╗     ███████╗ ██████╗ ██████╗  █████╗ ███╗   ███╗"
echo -e "╚══██╔══╝██╔════╝██║     ██╔════╝██╔════╝ ██╔══██╗██╔══██╗████╗ ████║"
echo -e "   ██║   █████╗  ██║     █████╗  ██║  ███╗██████╔╝███████║██╔████╔██║"
echo -e "   ██║   ██╔══╝  ██║     ██╔══╝  ██║   ██║██╔══██╗██╔══██║██║╚██╔╝██║"
echo -e "   ██║   ███████╗███████╗███████╗╚██████╔╝██║  ██║██║  ██║██║ ╚═╝ ██║"
echo -e "   ╚═╝   ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝"
echo -e ""
echo -e "███████╗███████╗██╗     ███████╗██████╗  ██████╗ ████████╗"
echo -e "██╔════╝██╔════╝██║     ██╔════╝██╔══██╗██╔═══██╗╚══██╔══╝"
echo -e "███████╗█████╗  ██║     █████╗  ██████╔╝██║   ██║   ██║   "
echo -e "╚════██║██╔══╝  ██║     ██╔══╝  ██╔══██╗██║   ██║   ██║   "
echo -e "███████║███████╗███████╗██║     ██████╔╝╚██████╔╝   ██║   "
echo -e "╚══════╝╚══════╝╚══════╝╚═╝     ╚═════╝  ╚═════╝    ╚═╝   "
echo -e "${NC}"
echo -e "${YELLOW}نصب و راه‌اندازی سلف بات تلگرام${NC}\n"

# تنظیم متغیرها
INSTALL_DIR=$(pwd)
ENV_FILE="$INSTALL_DIR/.env"
PYTHON_MIN_VERSION="3.10"

# بررسی نصب بودن پیش‌نیازها
check_dependencies() {
    echo -e "${YELLOW}بررسی پیش‌نیازها...${NC}"
    
    # بررسی نصب بودن Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}Python نصب نشده است. لطفاً ابتدا Python نسخه $PYTHON_MIN_VERSION یا بالاتر را نصب کنید.${NC}"
        exit 1
    fi
    
    # بررسی نسخه Python
    PYTHON_VERSION=$(python3 --version | cut -d ' ' -f 2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d '.' -f 1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d '.' -f 2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        echo -e "${RED}نسخه Python باید $PYTHON_MIN_VERSION یا بالاتر باشد. نسخه فعلی: $PYTHON_VERSION${NC}"
        exit 1
    fi
    
    # بررسی نصب بودن pip
    if ! command -v pip3 &> /dev/null; then
        echo -e "${RED}pip نصب نشده است. لطفاً pip را نصب کنید.${NC}"
        exit 1
    fi
    
    # بررسی نصب بودن docker (اختیاری)
    if ! command -v docker &> /dev/null; then
        echo -e "${YELLOW}هشدار: Docker نصب نشده است. اگر می‌خواهید از نصب داکری استفاده کنید، باید Docker را نصب کنید.${NC}"
        HAS_DOCKER=false
    else
        HAS_DOCKER=true
    fi
    
    # بررسی نصب بودن docker-compose (اختیاری)
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${YELLOW}هشدار: Docker Compose نصب نشده است. اگر می‌خواهید از نصب داکری استفاده کنید، باید Docker Compose را نصب کنید.${NC}"
        HAS_DOCKER_COMPOSE=false
    else
        HAS_DOCKER_COMPOSE=true
    fi
    
    echo -e "${GREEN}تمام پیش‌نیازهای اصلی نصب شده‌اند.${NC}"
}

# ایجاد فایل .env
create_env_file() {
    echo -e "${YELLOW}ایجاد فایل تنظیمات...${NC}"
    
    if [ -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}فایل .env از قبل وجود دارد. آیا می‌خواهید آن را بازنویسی کنید؟ (y/n)${NC}"
        read -r overwrite
        
        if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
            echo -e "${GREEN}فایل .env حفظ شد.${NC}"
            return
        fi
    fi
    
    # دریافت اطلاعات مورد نیاز
    echo -e "${GREEN}لطفاً اطلاعات لازم برای راه‌اندازی را وارد کنید:${NC}"
    
    # API تلگرام
    echo -e "${YELLOW}API ID تلگرام:${NC}"
    read -r API_ID
    
    echo -e "${YELLOW}API Hash تلگرام:${NC}"
    read -r API_HASH
    
    # رمز عبور برای رمزنگاری
    echo -e "${YELLOW}رمز عبور برای رمزنگاری (اگر وارد نکنید، به صورت خودکار ایجاد می‌شود):${NC}"
    read -r CRYPTO_KEY
    
    if [ -z "$CRYPTO_KEY" ]; then
        CRYPTO_KEY=$(openssl rand -hex 16)
        echo -e "${GREEN}رمز عبور به صورت خودکار ایجاد شد: $CRYPTO_KEY${NC}"
    fi
    
    # کلید راز برای JWT
    SECRET_KEY=$(openssl rand -hex 32)
    
    # ایجاد فایل .env
    cat > "$ENV_FILE" << EOF
# تنظیمات API تلگرام
API_ID=$API_ID
API_HASH=$API_HASH

# تنظیمات دیتابیس
SUPABASE_URL=http://localhost:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0

# تنظیمات Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# تنظیمات امنیتی
SECRET_KEY=$SECRET_KEY
CRYPTO_KEY=$CRYPTO_KEY

# تنظیمات عمومی
LOG_LEVEL=INFO
COMMAND_PREFIX=.
DEFAULT_LANGUAGE=fa
EOF
    
    echo -e "${GREEN}فایل .env با موفقیت ایجاد شد.${NC}"
}

# نصب با استفاده از docker
install_with_docker() {
    echo -e "${YELLOW}نصب با استفاده از Docker...${NC}"
    
    if [ "$HAS_DOCKER" = false ] || [ "$HAS_DOCKER_COMPOSE" = false ]; then
        echo -e "${RED}برای نصب با Docker، باید Docker و Docker Compose نصب شده باشند.${NC}"
        return 1
    fi
    
    # ساخت و راه‌اندازی کانتینرها
    echo -e "${YELLOW}در حال ساخت و راه‌اندازی کانتینرها...${NC}"
    docker-compose up -d
    
    # بررسی وضعیت کانتینرها
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}کانتینرها با موفقیت ساخته و راه‌اندازی شدند.${NC}"
        echo -e "${GREEN}وب پنل در آدرس http://localhost:3000 در دسترس است.${NC}"
        echo -e "${GREEN}API در آدرس http://localhost:8000 در دسترس است.${NC}"
        return 0
    else
        echo -e "${RED}خطا در ساخت و راه‌اندازی کانتینرها.${NC}"
        return 1
    fi
}

# نصب مستقیم
install_directly() {
    echo -e "${YELLOW}نصب مستقیم...${NC}"
    
    # ایجاد محیط مجازی
    echo -e "${YELLOW}ایجاد محیط مجازی...${NC}"
    python3 -m venv venv
    
    # فعال‌سازی محیط مجازی
    echo -e "${YELLOW}فعال‌سازی محیط مجازی...${NC}"
    source venv/bin/activate || . venv/bin/activate
    
    # نصب وابستگی‌ها
    echo -e "${YELLOW}نصب وابستگی‌ها...${NC}"
    pip install -r requirements.txt
    
    # ایجاد پوشه‌های مورد نیاز
    echo -e "${YELLOW}ایجاد پوشه‌های مورد نیاز...${NC}"
    mkdir -p data logs config plugins
    
    echo -e "${GREEN}نصب با موفقیت انجام شد.${NC}"
    echo -e "${GREEN}برای اجرای برنامه از دستور زیر استفاده کنید:${NC}"
    echo -e "${YELLOW}source venv/bin/activate && python main.py${NC}"
    
    return 0
}

# اجرای اسکریپت
main() {
    # بررسی پیش‌نیازها
    check_dependencies
    
    # ایجاد فایل .env
    create_env_file
    
    # انتخاب روش نصب
    echo -e "${YELLOW}روش نصب را انتخاب کنید:${NC}"
    echo -e "1) نصب با Docker (توصیه می‌شود)"
    echo -e "2) نصب مستقیم (نیاز به پیش‌نیازهای بیشتر دارد)"
    read -r install_method
    
    case $install_method in
        1)
            install_with_docker
            ;;
        2)
            install_directly
            ;;
        *)
            echo -e "${RED}انتخاب نامعتبر. خروج...${NC}"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}نصب و راه‌اندازی سلف بات تلگرام با موفقیت انجام شد!${NC}"
    echo -e "${GREEN}برای اطلاعات بیشتر، به مستندات مراجعه کنید: docs/user_guide/README.md${NC}"
}

# اجرای تابع اصلی
main
