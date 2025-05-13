import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'

// تنظیم سرور شبیه‌سازی شده API
export const server = setupWorker(...handlers)
