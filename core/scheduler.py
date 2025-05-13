"""
سیستم زمان‌بندی وظایف (مشابه cron) برای اجرای خودکار فعالیت‌ها در زمان‌های مشخص
"""
import asyncio
import datetime
import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass, field, asdict
import json
import os

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    """
    وظیفه زمان‌بندی شده
    """
    id: str
    name: str
    func: Callable
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    interval: Optional[int] = None  # فاصله زمانی به ثانیه
    cron: Optional[str] = None  # عبارت cron
    start_time: Optional[float] = None  # زمان شروع (timestamp)
    end_time: Optional[float] = None  # زمان پایان (timestamp)
    times: Optional[int] = None  # تعداد دفعات اجرا (None = بی‌نهایت)
    executed_count: int = 0  # تعداد دفعات اجرا شده
    last_executed: Optional[float] = None  # آخرین زمان اجرا
    next_execution: Optional[float] = None  # زمان اجرای بعدی
    is_enabled: bool = True  # وضعیت فعال بودن

    def to_dict(self) -> Dict[str, Any]:
        """
        تبدیل به دیکشنری برای ذخیره‌سازی

        Returns:
            Dict[str, Any]: دیکشنری
        """
        result = asdict(self)
        # حذف موارد غیرقابل سریالایز
        del result['func']
        return result


class CronParser:
    """
    پارسر عبارات cron
    """
    @staticmethod
    def parse(expr: str) -> Dict[str, Set[int]]:
        """
        تجزیه عبارت cron

        Args:
            expr: عبارت cron

        Returns:
            Dict[str, Set[int]]: مقادیر هر بخش
        """
        parts = expr.split()
        if len(parts) != 5:
            raise ValueError("عبارت cron باید شامل 5 بخش باشد")

        result = {
            'minute': CronParser._parse_field(parts[0], 0, 59),
            'hour': CronParser._parse_field(parts[1], 0, 23),
            'day': CronParser._parse_field(parts[2], 1, 31),
            'month': CronParser._parse_field(parts[3], 1, 12),
            'weekday': CronParser._parse_field(parts[4], 0, 6)
        }

        return result

    @staticmethod
    def _parse_field(field: str, min_val: int, max_val: int) -> Set[int]:
        """
        تجزیه یک بخش از عبارت cron

        Args:
            field: بخش
            min_val: حداقل مقدار
            max_val: حداکثر مقدار

        Returns:
            Set[int]: مجموعه مقادیر
        """
        if field == '*':
            return set(range(min_val, max_val + 1))

        values = set()

        for part in field.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                values.update(range(start, end + 1))
            elif '/' in part:
                if part.startswith('*/'):
                    start, step = min_val, int(part.split('/')[1])
                    values.update(range(start, max_val + 1, step))
                else:
                    range_val, step = part.split('/')
                    if '-' in range_val:
                        start, end = map(int, range_val.split('-'))
                    else:
                        start, end = int(range_val), max_val
                    values.update(range(start, end + 1, int(step)))
            else:
                values.add(int(part))

        return values

    @staticmethod
    def matches(cron_parts: Dict[str, Set[int]], dt: datetime.datetime) -> bool:
        """
        بررسی تطابق زمان با الگوی cron

        Args:
            cron_parts: بخش‌های cron
            dt: زمان

        Returns:
            bool: نتیجه بررسی
        """
        return (
            dt.minute in cron_parts['minute'] and
            dt.hour in cron_parts['hour'] and
            dt.day in cron_parts['day'] and
            dt.month in cron_parts['month'] and
            dt.weekday() in cron_parts['weekday']
        )

    @staticmethod
    def get_next_execution(cron_parts: Dict[str, Set[int]], now: datetime.datetime) \
        -> datetime.datetime: \
        """
        محاسبه زمان اجرای بعدی

        Args:
            cron_parts: بخش‌های cron
            now: زمان فعلی

        Returns:
            datetime.datetime: زمان اجرای بعدی
        """
        # شروع از یک دقیقه بعد
        next_time = now + datetime.timedelta(minutes=1)
        next_time = next_time.replace(second=0, microsecond=0)

        # حداکثر 1 سال جلو می‌رویم (برای جلوگیری از حلقه بی‌نهایت)
        max_time = now + datetime.timedelta(days=365)

        while next_time < max_time:
            if CronParser.matches(cron_parts, next_time):
                return next_time
            next_time += datetime.timedelta(minutes=1)

        # اگر در محدوده زمانی پیدا نشد، یک زمان پیش‌فرض برمی‌گردانیم
        return max_time


class Scheduler:
    """
    مدیریت زمان‌بندی وظایف
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Scheduler, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.tasks: Dict[str, ScheduledTask] = {}
        self.cron_expressions: Dict[str, Dict[str, Set[int]]] = {}
        self.running = False
        self.loop = None
        self.data_file = "data/scheduler_tasks.json"
        self.load_tasks()

    def load_tasks(self) -> bool:
        """
        بارگذاری وظایف ذخیره شده

        Returns:
            bool: وضعیت بارگذاری
        """
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    tasks_data = json.load(f)
                    # توجه: توابع قابل سریالایز نیستند و باید جداگانه بارگذاری شوند
                    logger.info(f"{len(tasks_data)} وظیفه از فایل بارگذاری شد")
            return True
        except Exception as e:
            logger.error(f"خطا در بارگذاری وظایف: {str(e)}")
            return False

    def save_tasks(self) -> bool:
        """
        ذخیره وظایف

        Returns:
            bool: وضعیت ذخیره‌سازی
        """
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            tasks_data = {task_id: task.to_dict() for task_id, task in self.tasks.items()}
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(tasks_data, f, ensure_ascii=False, indent=2)
            logger.info(f"{len(tasks_data)} وظیفه در فایل ذخیره شد")
            return True
        except Exception as e:
            logger.error(f"خطا در ذخیره وظایف: {str(e)}")
            return False

    def schedule(
        self,
        func: Callable,
        interval: Optional[int] = None,
        cron: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        times: Optional[int] = None,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        *args,
        **kwargs
    ) -> str:
        """
        زمان‌بندی یک وظیفه

        Args:
            func: تابع
            interval: فاصله زمانی (ثانیه)
            cron: عبارت cron
            start_time: زمان شروع (timestamp)
            end_time: زمان پایان (timestamp)
            times: تعداد دفعات اجرا
            name: نام وظیفه
            task_id: شناسه وظیفه (اختیاری)
            *args: پارامترهای تابع
            **kwargs: پارامترهای تابع

        Returns:
            str: شناسه وظیفه
        """
        # بررسی پارامترها
        if not interval and not cron:
            raise ValueError("یا interval یا cron باید مشخص شود")

        if interval and interval <= 0:
            raise ValueError("interval باید بزرگتر از صفر باشد")

        # ایجاد شناسه یکتا
        if not task_id:
            task_id = str(uuid.uuid4())

        # تنظیم نام پیش‌فرض
        if not name:
            name = func.__name__

        # محاسبه زمان اجرای بعدی
        now = time.time()
        next_execution = start_time if start_time and start_time > now else now

        if cron:
            cron_parts = CronParser.parse(cron)
            self.cron_expressions[task_id] = cron_parts
            next_dt = CronParser.get_next_execution(cron_parts, datetime.datetime.now())
            next_execution = next_dt.timestamp()

        # ایجاد وظیفه
        task = ScheduledTask(
            id=task_id,
            name=name,
            func=func,
            args=args,
            kwargs=kwargs,
            interval=interval,
            cron=cron,
            start_time=start_time,
            end_time=end_time,
            times=times,
            next_execution=next_execution
        )

        # ذخیره وظیفه
        self.tasks[task_id] = task
        self.save_tasks()

        logger.info(f"وظیفه {name} (ID: {task_id}) زمان‌بندی شد")
        return task_id

    def schedule_once(
        self,
        func: Callable,
        when: float,
        name: Optional[str] = None,
        task_id: Optional[str] = None,
        *args,
        **kwargs
    ) -> str:
        """
        زمان‌بندی یک وظیفه یکبارمصرف

        Args:
            func: تابع
            when: زمان اجرا (timestamp)
            name: نام وظیفه
            task_id: شناسه وظیفه (اختیاری)
            *args: پارامترهای تابع
            **kwargs: پارامترهای تابع

        Returns:
            str: شناسه وظیفه
        """
        return self.schedule(
            func,
            interval=None,
            cron=None,
            start_time=when,
            end_time=None,
            times=1,
            name=name,
            task_id=task_id,
            *args,
            **kwargs
        )

    def unschedule(self, task_id: str) -> bool:
        """
        لغو زمان‌بندی وظیفه

        Args:
            task_id: شناسه وظیفه

        Returns:
            bool: وضعیت لغو
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            if task_id in self.cron_expressions:
                del self.cron_expressions[task_id]
            self.save_tasks()
            logger.info(f"وظیفه با ID {task_id} لغو شد")
            return True
        return False

    def pause_task(self, task_id: str) -> bool:
        """
        توقف موقت وظیفه

        Args:
            task_id: شناسه وظیفه

        Returns:
            bool: وضعیت توقف
        """
        if task_id in self.tasks:
            self.tasks[task_id].is_enabled = False
            self.save_tasks()
            logger.info(f"وظیفه با ID {task_id} متوقف شد")
            return True
        return False

    def resume_task(self, task_id: str) -> bool:
        """
        ادامه وظیفه

        Args:
            task_id: شناسه وظیفه

        Returns:
            bool: وضعیت ادامه
        """
        if task_id in self.tasks:
            self.tasks[task_id].is_enabled = True
            self.save_tasks()
            logger.info(f"وظیفه با ID {task_id} از سر گرفته شد")
            return True
        return False

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """
        دریافت اطلاعات وظیفه

        Args:
            task_id: شناسه وظیفه

        Returns:
            Optional[ScheduledTask]: اطلاعات وظیفه یا None
        """
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        لیست تمام وظایف

        Returns:
            List[Dict[str, Any]]: لیست وظایف
        """
        return [task.to_dict() for task in self.tasks.values()]

    async def run(self):
        """
        اجرای زمان‌بندی
        """
        self.running = True
        self.loop = asyncio.get_event_loop()

        try:
            while self.running:
                now = time.time()

                # بررسی وظایف
                for task_id, task in list(self.tasks.items()):
                    # تنها وظایف فعال بررسی شوند
                    if not task.is_enabled:
                        continue

                    # بررسی زمان شروع
                    if task.start_time and now < task.start_time:
                        continue

                    # بررسی زمان پایان
                    if task.end_time and now > task.end_time:
                        # حذف وظایف منقضی
                        del self.tasks[task_id]
                        if task_id in self.cron_expressions:
                            del self.cron_expressions[task_id]
                        continue

                    # بررسی تعداد دفعات اجرا
                    if task.times is not None and task.executed_count >= task.times:
                        # حذف وظایف تکمیل شده
                        del self.tasks[task_id]
                        if task_id in self.cron_expressions:
                            del self.cron_expressions[task_id]
                        continue

                    # بررسی زمان اجرای بعدی
                    if task.next_execution and now >= task.next_execution:
                        # اجرای وظیفه
                        try:
                            if asyncio.iscoroutinefunction(task.func):
                                asyncio.create_task(task.func(*task.args, **task.kwargs))
                            else:
                                self.loop.run_in_executor(
                                    None, lambda: task.func(*task.args, **task.kwargs)
                                )

                            # بروزرسانی آمار
                            task.executed_count += 1
                            task.last_executed = now

                            # محاسبه زمان اجرای بعدی
                            if task.interval:
                                task.next_execution = now + task.interval
                            elif task.cron and task_id in self.cron_expressions:
                                cron_parts = self.cron_expressions[task_id]
                                next_dt = CronParser.get_next_execution(
                                    cron_parts,
                                    datetime.datetime.fromtimestamp(now)
                                )
                                task.next_execution = next_dt.timestamp()
                            elif task.times is not None and task.executed_count >= task.times:
                                # حذف وظایف تکمیل شده
                                del self.tasks[task_id]
                                if task_id in self.cron_expressions:
                                    del self.cron_expressions[task_id]
                                continue

                            logger.info(f"وظیفه {task.name} (ID: {task_id}) اجرا شد")
                        except Exception as e:
                            logger.error(f"خطا در اجرای وظیفه {task.name} (ID: {task_id}): {str(e)}")

                # ذخیره وظایف بروز شده
                self.save_tasks()

                # انتظار برای نوبت بعدی (بررسی هر ثانیه)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("زمان‌بندی لغو شد")
            self.running = False
        except Exception as e:
            logger.error(f"خطا در اجرای زمان‌بندی: {str(e)}")
            self.running = False

    def start(self):
        """
        شروع زمان‌بندی (غیر بلاکینگ)
        """
        if not self.running:
            logger.info("زمان‌بندی شروع شد")
            asyncio.create_task(self.run())

    def stop(self):
        """
        توقف زمان‌بندی
        """
        logger.info("زمان‌بندی متوقف شد")
        self.running = False


# دکوراتورهای کمکی برای زمان‌بندی

def cron(expr: str, name: Optional[str] = None):
    """
    دکوراتور برای زمان‌بندی با عبارت cron

    Args:
        expr: عبارت cron
        name: نام وظیفه

    Returns:
        Callable: دکوراتور
    """
    def decorator(func):
        scheduler = Scheduler()
        scheduler.schedule(func, cron=expr, name=name or func.__name__)
        return func
    return decorator

def interval(seconds: int, name: Optional[str] = None):
    """
    دکوراتور برای زمان‌بندی با فاصله زمانی

    Args:
        seconds: فاصله زمانی (ثانیه)
        name: نام وظیفه

    Returns:
        Callable: دکوراتور
    """
    def decorator(func):
        scheduler = Scheduler()
        scheduler.schedule(func, interval=seconds, name=name or func.__name__)
        return func
    return decorator

def once(when: float, name: Optional[str] = None):
    """
    دکوراتور برای زمان‌بندی یکبارمصرف

    Args:
        when: زمان اجرا (timestamp)
        name: نام وظیفه

    Returns:
        Callable: دکوراتور
    """
    def decorator(func):
        scheduler = Scheduler()
        scheduler.schedule_once(func, when, name=name or func.__name__)
        return func
    return decorator
