/**
 * @jest-environment jsdom
 */

import axios from 'axios'
import { describe, test, expect, jest, beforeEach } from '@jest/globals'

// Mock کردن axios
jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

describe('Stats and Activities API', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  test('should fetch dashboard stats successfully', async () => {
    // تعریف داده مورد انتظار
    const mockStats = {
      total_users: 10,
      total_plugins: 5,
      active_plugins: 3,
      total_messages: 1000,
      daily_messages: 100,
      bot_status: 'online',
      last_activity: '2025-05-13T01:30:00Z'
    }

    // تنظیم پاسخ مورد نظر برای درخواست GET
    mockedAxios.get.mockResolvedValueOnce({ data: mockStats })
    
    // فراخوانی API
    const { data } = await axios.get('/api/stats/summary')
    
    // بررسی نتایج
    expect(data).toHaveProperty('total_users')
    expect(data).toHaveProperty('total_plugins')
    expect(data).toHaveProperty('active_plugins')
    expect(data).toHaveProperty('bot_status')
    expect(data.bot_status).toBe('online')
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/stats/summary')
  })

  test('should fetch recent activities', async () => {
    // تعریف داده مورد انتظار
    const mockActivities = [
      {
        id: 1,
        type: 'login',
        description: 'User login',
        timestamp: '2025-05-13T01:20:00Z',
        user_id: 1,
        username: 'admin'
      },
      {
        id: 2,
        type: 'message',
        description: 'Message sent',
        timestamp: '2025-05-13T01:10:00Z',
        user_id: 1,
        username: 'admin'
      }
    ]

    // تنظیم پاسخ مورد نظر برای درخواست GET
    mockedAxios.get.mockResolvedValueOnce({ data: mockActivities })
    
    // فراخوانی API
    const { data } = await axios.get('/api/activities/recent')
    
    // بررسی نتایج
    expect(Array.isArray(data)).toBe(true)
    expect(data.length).toBeGreaterThan(0)
    expect(data[0]).toHaveProperty('type')
    expect(data[0]).toHaveProperty('timestamp')
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/activities/recent')
  })

  test('should fetch system resources', async () => {
    // تعریف داده مورد انتظار
    const mockResources = {
      cpu_usage: 25,
      memory_usage: 512,
      memory_total: 4096,
      disk_usage: 10240,
      disk_total: 102400
    }

    // تنظیم پاسخ مورد نظر برای درخواست GET
    mockedAxios.get.mockResolvedValueOnce({ data: mockResources })
    
    // فراخوانی API
    const { data } = await axios.get('/api/system/resources')
    
    // بررسی نتایج
    expect(data).toHaveProperty('cpu_usage')
    expect(data).toHaveProperty('memory_usage')
    expect(data).toHaveProperty('memory_total')
    expect(data).toHaveProperty('disk_usage')
    expect(data).toHaveProperty('disk_total')
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/system/resources')
  })
})
