"""
سیستم مدیریت وظایف پس‌زمینه با استفاده از Redis برای پردازش وظایف زمان‌بر
"""
import asyncio
import functools
import logging
import json
import os
import signal
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field, asdict
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor

from core.database.redis import RedisManager

# تنظیم سیستم لاگینگ
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("data/logs/background_tasks.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# نوع‌های وظایف
class TaskPriority:
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class TaskStatus:
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


@dataclass
class Task:
    """
    وظیفه پس‌زمینه
    """
    id: str
    name: str
    function_name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: str = TaskPriority.NORMAL
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    status: str = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0
    max_retries: int = 3
    retries: int = 0
    module_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        تبدیل به دیکشنری

        Returns:
            Dict[str, Any]: دیکشنری
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """
        ساخت از دیکشنری

        Args:
            data: دیکشنری

        Returns:
            Task: شیء وظیفه
        """
        return cls(**data)


class TaskManager:
    """
    مدیریت وظایف پس‌زمینه
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskManager, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance

    def initialize(self):
        """
        مقداردهی اولیه
        """
        self.redis = RedisManager()
        self.tasks: Dict[str, Task] = {}
        self.running = False
        self.loop = None
        self.thread_pool = ThreadPoolExecutor(max_workers=5)
        self.process_pool = ProcessPoolExecutor(max_workers=3)

        # کلیدهای Redis
        self.queue_prefix = "task_queue:"
        self.task_prefix = "task:"
        self.result_prefix = "task_result:"

        # بارگذاری وظایف موجود
        self.load_tasks()

    def load_tasks(self):
        """
        بارگذاری وظایف موجود از Redis
        """
        try:
            # دریافت کلیدهای تمام وظایف
            keys = self.redis.redis_client.keys(f"{self.task_prefix}*")
            for key in keys:
                task_id = key.decode('utf-8').replace(self.task_prefix, "")
                task_data = self.redis.get(key.decode('utf-8'))
                if task_data:
                    task = Task.from_dict(task_data)
                    self.tasks[task_id] = task

            logger.info(f"{len(self.tasks)} وظیفه از Redis بارگذاری شد")
        except Exception as e:
            logger.error(f"خطا در بارگذاری وظایف: {str(e)}")

    def create_task(
        self,
        function: Union[str, Callable],
        name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
        priority: str = TaskPriority.NORMAL,
        max_retries: int = 3,
        module_path: Optional[str] = None
    ) -> str:
        """
        ایجاد یک وظیفه جدید

        Args:
            function: تابع یا نام تابع
            name: نام وظیفه
            args: پارامترهای پوزیشنال
            kwargs: پارامترهای کلیدی
            priority: اولویت
            max_retries: حداکثر تلاش مجدد
            module_path: مسیر ماژول

        Returns:
            str: شناسه وظیفه
        """
        task_id = str(uuid.uuid4())
        function_name = function if isinstance(function, str) else function.__name__

        # ذخیره مسیر ماژول برای توابع دینامیک
        if not module_path and not isinstance(function, str):
            try:
                module_path = function.__module__
            except AttributeError:
                module_path = None

        task = Task(
            id=task_id,
            name=name,
            function_name=function_name,
            args=args or [],
            kwargs=kwargs or {},
            priority=priority,
            max_retries=max_retries,
            module_path=module_path
        )

        # ذخیره وظیفه
        self.tasks[task_id] = task
        self.redis.set(f"{self.task_prefix}{task_id}", task.to_dict())

        # افزودن به صف
        self.redis.enqueue(f"{self.queue_prefix}{priority}", task_id)

        logger.info(f"وظیفه {name} (ID: {task_id}) ایجاد شد")
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        """
        دریافت وظیفه

        Args:
            task_id: شناسه وظیفه

        Returns:
            Optional[Task]: وظیفه یا None
        """
        if task_id in self.tasks:
            return self.tasks[task_id]

        # تلاش برای دریافت از Redis
        task_data = self.redis.get(f"{self.task_prefix}{task_id}")
        if task_data:
            task = Task.from_dict(task_data)
            self.tasks[task_id] = task
            return task

        return None

    def cancel_task(self, task_id: str) -> bool:
        """
        لغو وظیفه

        Args:
            task_id: شناسه وظیفه

        Returns:
            bool: وضعیت لغو
        """
        task = self.get_task(task_id)
        if not task:
            return False

        if task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
            task.status = TaskStatus.CANCELED
            self.redis.set(f"{self.task_prefix}{task_id}", task.to_dict())
            logger.info(f"وظیفه {task.name} (ID: {task_id}) لغو شد")
            return True

        return False

    def update_task_progress(self, task_id: str, progress: float) -> bool:
        """
        بروزرسانی پیشرفت وظیفه

        Args:
            task_id: شناسه وظیفه
            progress: پیشرفت (0.0 تا 1.0)

        Returns:
            bool: وضعیت بروزرسانی
        """
        task = self.get_task(task_id)
        if not task:
            return False

        task.progress = min(max(progress, 0.0), 1.0)
        self.redis.set(f"{self.task_prefix}{task_id}", task.to_dict())
        return True

    def list_tasks(self, status: Optional[str] = None) -> List[Task]:
        """
        لیست وظایف

        Args:
            status: وضعیت فیلتر

        Returns:
            List[Task]: لیست وظایف
        """
        if status:
            return [task for task in self.tasks.values() if task.status == status]
        return list(self.tasks.values())

    def clear_completed_tasks(self, age: int = 86400) -> int:
        """
        پاکسازی وظایف تکمیل شده

        Args:
            age: سن به ثانیه

        Returns:
            int: تعداد وظایف پاکسازی شده
        """
        now = time.time()
        cleared_count = 0

        for task_id, task in list(self.tasks.items()):
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED]:
                if task.completed_at and now - task.completed_at > age:
                    # حذف از حافظه
                    del self.tasks[task_id]

                    # حذف از Redis
                    self.redis.delete(f"{self.task_prefix}{task_id}")
                    self.redis.delete(f"{self.result_prefix}{task_id}")

                    cleared_count += 1

        logger.info(f"{cleared_count} وظیفه قدیمی پاکسازی شد")
        return cleared_count

    def _load_function(self, function_name: str, module_path: Optional[str] = None) \
        -> Optional[Callable]: \
        """
        بارگذاری دینامیک تابع

        Args:
            function_name: نام تابع
            module_path: مسیر ماژول

        Returns:
            Optional[Callable]: تابع یا None
        """
        try:
            if module_path:
                if module_path not in sys.modules:
                    __import__(module_path)
                module = sys.modules[module_path]
                return getattr(module, function_name)
            else:
                # جستجو در ماژول‌های اصلی برنامه
                for module_name in ['core', 'plugins']:
                    try:
                        module = __import__(f"{module_name}.{function_name}", fromlist=[function_name])
                        return getattr(module, function_name)
                    except (ImportError, AttributeError):
                        pass

            logger.error(f"تابع {function_name} یافت نشد")
            return None
        except Exception as e:
            logger.error(f"خطا در بارگذاری تابع {function_name}: {str(e)}")
            return None

    async def _execute_task(self, task: Task):
        """
        اجرای یک وظیفه

        Args:
            task: وظیفه
        """
        # بروزرسانی وضعیت
        task.status = TaskStatus.RUNNING
        task.started_at = time.time()
        self.redis.set(f"{self.task_prefix}{task.id}", task.to_dict())

        try:
            # بارگذاری تابع
            function = self._load_function(task.function_name, task.module_path)
            if not function:
                raise ValueError(f"تابع {task.function_name} یافت نشد")

            # تصمیم‌گیری برای نحوه اجرا
            is_coroutine = asyncio.iscoroutinefunction(function)

            # اجرای وظیفه
            if is_coroutine:
                result = await function(*task.args, **task.kwargs)
            else:
                # برای توابع CPU-bound، از ProcessPoolExecutor استفاده می‌کنیم
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.process_pool,
                    functools.partial(function, *task.args, **task.kwargs)
                )

            # ذخیره نتیجه
            task.result = result
            task.status = TaskStatus.COMPLETED
            task.completed_at = time.time()
            task.progress = 1.0

            logger.info(f"وظیفه {task.name} (ID: {task.id}) با موفقیت تکمیل شد")
        except Exception as e:
            # ثبت خطا
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = time.time()

            # بررسی تلاش مجدد
            if task.retries < task.max_retries:
                task.retries += 1
                task.status = TaskStatus.PENDING

                # افزودن مجدد به صف
                self.redis.enqueue(f"{self.queue_prefix}{task.priority}", task.id)

                logger.warning(f"وظیفه {task.name} (ID: {task.id}) با خطا مواجه شد، تلاش مجدد {task.retries}/{task.max_retries}")
            else:
                logger.error(f"وظیفه {task.name} (ID: {task.id}) با خطا شکست خورد: {str(e)}")

        # ذخیره وضعیت نهایی
        self.redis.set(f"{self.task_prefix}{task.id}", task.to_dict())

        # ذخیره نتیجه در Redis جداگانه برای مدیریت حافظه بهتر
        if task.status == TaskStatus.COMPLETED:
            try:
                self.redis.set(f"{self.result_prefix}{task.id}", task.result)
            except Exception as e:
                logger.error(f"خطا در ذخیره نتیجه: {str(e)}")

    async def _process_queue(self, priority: str):
        """
        پردازش صف وظایف

        Args:
            priority: اولویت
        """
        queue_name = f"{self.queue_prefix}{priority}"

        while self.running:
            try:
                # دریافت یک وظیفه از صف
                task_id = self.redis.dequeue(queue_name, timeout=1)
                if not task_id:
                    await asyncio.sleep(0.1)
                    continue

                task = self.get_task(task_id)
                if not task:
                    logger.warning(f"وظیفه {task_id} یافت نشد")
                    continue

                # بررسی وضعیت
                if task.status != TaskStatus.PENDING:
                    continue

                # اجرای وظیفه
                asyncio.create_task(self._execute_task(task))
            except Exception as e:
                logger.error(f"خطا در پردازش صف {priority}: {str(e)}")
                await asyncio.sleep(1)

    async def run(self):
        """
        راه‌اندازی پردازشگر وظایف
        """
        self.running = True
        self.loop = asyncio.get_event_loop()

        # راه‌اندازی پردازشگرهای صف
        queue_processors = [
            self._process_queue(TaskPriority.HIGH),
            self._process_queue(TaskPriority.NORMAL),
            self._process_queue(TaskPriority.LOW)
        ]

        try:
            # اجرای همزمان تمام پردازشگرها
            await asyncio.gather(*queue_processors)
        except asyncio.CancelledError:
            logger.info("پردازشگر وظایف لغو شد")
            self.running = False
        except Exception as e:
            logger.error(f"خطا در اجرای پردازشگر وظایف: {str(e)}")
            self.running = False

    def start(self):
        """
        شروع پردازشگر (غیر بلاکینگ)
        """
        if not self.running:
            logger.info("پردازشگر وظایف شروع شد")
            asyncio.create_task(self.run())

    def stop(self):
        """
        توقف پردازشگر
        """
        logger.info("پردازشگر وظایف متوقف شد")
        self.running = False

        # بستن thread و process pool
        self.thread_pool.shutdown(wait=False)
        self.process_pool.shutdown(wait=False)


# تابع کمکی برای مدیریت وظایف پس‌زمینه
def run_in_background(name: str, priority: str = TaskPriority.NORMAL, max_retries: int = 3):
    """
    دکوراتور برای اجرای یک تابع در پس‌زمینه

    Args:
        name: نام وظیفه
        priority: اولویت
        max_retries: حداکثر تلاش مجدد

    Returns:
        Callable: دکوراتور
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            task_manager = TaskManager()
            task_id = task_manager.create_task(
                function=func,
                name=name,
                args=args,
                kwargs=kwargs,
                priority=priority,
                max_retries=max_retries
            )
            return task_id
        return wrapper
    return decorator


# تابع راه‌اندازی کارگر پس‌زمینه
def start_worker(num_processes: int = 2):
    """
    راه‌اندازی کارگر مستقل

    Args:
        num_processes: تعداد پردازش‌ها
    """
    # تنظیم مدیر تسک
    task_manager = TaskManager()

    # تنظیم signal handler
    def signal_handler(signum, frame):
        print("دریافت سیگنال توقف...")
        task_manager.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # شروع پردازش
    print(f"کارگر با {num_processes} پردازش شروع شد")

    # ایجاد لوپ جدید
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # شروع پردازشگر وظایف
        loop.run_until_complete(task_manager.run())
    except KeyboardInterrupt:
        print("کارگر متوقف شد")
    finally:
        task_manager.stop()
        loop.close()
