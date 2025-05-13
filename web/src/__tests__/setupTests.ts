// تنظیمات جست برای تمام تست‌ها

// راه‌اندازی mock برای DOM و تست‌های UI
import '@testing-library/jest-dom'

// تنظیم محیط تست
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

// mock کردن matchMedia برای تست کامپوننت‌هایی که از آن استفاده می‌کنند
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});
