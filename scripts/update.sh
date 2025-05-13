#!/bin/bash

# اسکریپت بروزرسانی سلف بات تلگرام
# این اسکریپت کد منبع را بروزرسانی کرده و تغییرات لازم را اعمال می‌کند

# تنظیم رنگ‌ها برای خروجی
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# تنظیم متغیرها
INSTALL_DIR=$(pwd)
BACKUP_DIR="$INSTALL_DIR/backups/$(date +%Y%m%d%H%M%S)"

# ایجاد پشتیبان
create_backup() {
    echo -e "${YELLOW}ایجاد پشتیبان از تنظیمات و داده‌ها...${NC}"
    
    # ایجاد پوشه پشتیبان
    mkdir -p "$BACKUP_DIR"
    
    # پشتیبان‌گیری از فایل‌های مهم
    cp -r "$INSTALL_DIR/data" "$BACKUP_DIR/" 2>/dev/null || true
    cp -r "$INSTALL_DIR/config" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$INSTALL_DIR/.env" "$BACKUP_DIR/" 2>/dev/null || true
    
    # پشتیبان‌گیری از پلاگین‌های سفارشی
    if [ -d "$INSTALL_DIR/plugins" ]; then
        # فقط پلاگین‌های سفارشی (غیر از پلاگین‌های پیش‌فرض) را پشتیبان‌گیری کنید
        mkdir -p "$BACKUP_DIR/plugins"
        
        # لیست پلاگین‌های پیش‌فرض
        DEFAULT_PLUGINS=("admin" "security" "tools" "ai" "analytics" "integration")
        
        # کپی پلاگین‌های سفارشی
        for plugin in "$INSTALL_DIR/plugins"/*; do
            if [ -d "$plugin" ]; then
                plugin_name=$(basename "$plugin")
                
                # بررسی اینکه آیا پلاگین پیش‌فرض است یا خیر
                is_default=false
                for default_plugin in "${DEFAULT_PLUGINS[@]}"; do
                    if [ "$plugin_name" = "$default_plugin" ]; then
                        is_default=true
                        break
                    fi
                done
                
                # اگر پلاگین پیش‌فرض نیست، پشتیبان‌گیری کنید
                if [ "$is_default" = false ]; then
                    cp -r "$plugin" "$BACKUP_DIR/plugins/"
                fi
            fi
        done
    fi
    
    echo -e "${GREEN}پشتیبان با موفقیت در مسیر $BACKUP_DIR ایجاد شد.${NC}"
}

# بروزرسانی با استفاده از git
update_from_git() {
    echo -e "${YELLOW}بروزرسانی از مخزن git...${NC}"
    
    # بررسی وجود گیت
    if ! command -v git &> /dev/null; then
        echo -e "${RED}git نصب نشده است. لطفاً ابتدا git را نصب کنید.${NC}"
        return 1
    fi
    
    # بررسی اینکه آیا دایرکتوری فعلی یک مخزن git است یا خیر
    if [ ! -d ".git" ]; then
        echo -e "${RED}دایرکتوری فعلی یک مخزن git نیست.${NC}"
        return 1
    fi
    
    # ذخیره تغییرات محلی
    git stash
    
    # بروزرسانی از مخزن اصلی
    git pull
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}کد منبع با موفقیت بروزرسانی شد.${NC}"
        return 0
    else
        echo -e "${RED}خطا در بروزرسانی کد منبع.${NC}"
        return 1
    fi
}

# بروزرسانی وابستگی‌ها
update_dependencies() {
    echo -e "${YELLOW}بروزرسانی وابستگی‌ها...${NC}"
    
    # بررسی روش نصب (docker یا مستقیم)
    if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
        # بروزرسانی با docker-compose
        echo -e "${YELLOW}بروزرسانی با استفاده از Docker...${NC}"
        docker-compose down
        docker-compose build --no-cache
        docker-compose up -d
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}کانتینرها با موفقیت بروزرسانی شدند.${NC}"
            return 0
        else
            echo -e "${RED}خطا در بروزرسانی کانتینرها.${NC}"
            return 1
        fi
    else
        # بروزرسانی در نصب مستقیم
        echo -e "${YELLOW}بروزرسانی وابستگی‌ها در نصب مستقیم...${NC}"
        
        # بررسی وجود محیط مجازی
        if [ -d "venv" ]; then
            # فعال‌سازی محیط مجازی
            source venv/bin/activate || . venv/bin/activate
            
            # بروزرسانی وابستگی‌ها
            pip install -r requirements.txt --upgrade
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}وابستگی‌ها با موفقیت بروزرسانی شدند.${NC}"
                return 0
            else
                echo -e "${RED}خطا در بروزرسانی وابستگی‌ها.${NC}"
                return 1
            fi
        else
            echo -e "${RED}محیط مجازی یافت نشد. آیا پروژه به درستی نصب شده است؟${NC}"
            return 1
        fi
    fi
}

# اجرای مهاجرت‌های دیتابیس
run_migrations() {
    echo -e "${YELLOW}اجرای مهاجرت‌های دیتابیس...${NC}"
    
    # بررسی روش نصب (docker یا مستقیم)
    if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
        # اجرای مهاجرت‌ها با docker-compose
        echo -e "${YELLOW}اجرای مهاجرت‌ها با استفاده از Docker...${NC}"
        docker-compose exec -T selfbot python -m database.migration_manager migrate
        
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}مهاجرت‌ها با موفقیت اجرا شدند.${NC}"
            return 0
        else
            echo -e "${RED}خطا در اجرای مهاجرت‌ها.${NC}"
            return 1
        fi
    else
        # اجرای مهاجرت‌ها در نصب مستقیم
        echo -e "${YELLOW}اجرای مهاجرت‌ها در نصب مستقیم...${NC}"
        
        # بررسی وجود محیط مجازی
        if [ -d "venv" ]; then
            # فعال‌سازی محیط مجازی
            source venv/bin/activate || . venv/bin/activate
            
            # اجرای مهاجرت‌ها
            python -m database.migration_manager migrate
            
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}مهاجرت‌ها با موفقیت اجرا شدند.${NC}"
                return 0
            else
                echo -e "${RED}خطا در اجرای مهاجرت‌ها.${NC}"
                return 1
            fi
        else
            echo -e "${RED}محیط مجازی یافت نشد. آیا پروژه به درستی نصب شده است؟${NC}"
            return 1
        fi
    fi
}

# بازگرداندن پلاگین‌های سفارشی
restore_custom_plugins() {
    echo -e "${YELLOW}بازگرداندن پلاگین‌های سفارشی...${NC}"
    
    if [ -d "$BACKUP_DIR/plugins" ]; then
        # کپی پلاگین‌های سفارشی از پشتیبان
        cp -r "$BACKUP_DIR/plugins"/* "$INSTALL_DIR/plugins/" 2>/dev/null || true
        echo -e "${GREEN}پلاگین‌های سفارشی با موفقیت بازگردانده شدند.${NC}"
    else
        echo -e "${YELLOW}پلاگین سفارشی در پشتیبان یافت نشد.${NC}"
    fi
}

# اجرای اسکریپت
main() {
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
    echo -e "${YELLOW}بروزرسانی سلف بات تلگرام${NC}\n"
    
    # ایجاد پشتیبان
    create_backup
    
    # بروزرسانی کد منبع
    update_from_git
    git_update_result=$?
    
    # بروزرسانی وابستگی‌ها
    update_dependencies
    dep_update_result=$?
    
    # اجرای مهاجرت‌های دیتابیس
    run_migrations
    migration_result=$?
    
    # بازگرداندن پلاگین‌های سفارشی
    restore_custom_plugins
    
    # نمایش نتیجه نهایی
    echo -e "\n${YELLOW}نتیجه بروزرسانی:${NC}"
    
    if [ $git_update_result -eq 0 ] && [ $dep_update_result -eq 0 ] && [ $migration_result -eq 0 ]; then
        echo -e "${GREEN}بروزرسانی با موفقیت انجام شد!${NC}"
        echo -e "${GREEN}پشتیبان در مسیر $BACKUP_DIR ذخیره شده است.${NC}"
        echo -e "${GREEN}برای شروع مجدد سرویس، از دستورات زیر استفاده کنید:${NC}"
        
        if [ -f "docker-compose.yml" ] && command -v docker-compose &> /dev/null; then
            echo -e "${YELLOW}docker-compose restart${NC}"
        else
            echo -e "${YELLOW}source venv/bin/activate && python main.py${NC}"
        fi
    else
        echo -e "${RED}بروزرسانی با خطا مواجه شد.${NC}"
        echo -e "${YELLOW}می‌توانید پشتیبان را از مسیر $BACKUP_DIR بازیابی کنید.${NC}"
    fi
}

# اجرای تابع اصلی
main
