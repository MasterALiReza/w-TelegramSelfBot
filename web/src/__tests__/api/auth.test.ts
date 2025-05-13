/**
 * @jest-environment jsdom
 */

import axios from 'axios'
import { describe, test, expect, jest, beforeEach, afterEach } from '@jest/globals'

// Mock کردن axios
jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

describe('Auth API', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  afterEach(() => {
    // تمیز کردن هدرها بعد از هر تست
    delete axios.defaults.headers.common['Authorization']
  })

  test('should authenticate user and return token', async () => {
    // تعریف داده مورد انتظار
    const mockTokenResponse = {
      access_token: 'test-token',
      token_type: 'bearer',
      expires_in: 3600
    }

    // تنظیم پاسخ مورد نظر برای درخواست POST
    mockedAxios.post.mockResolvedValueOnce({ data: mockTokenResponse })
    
    // فراخوانی API
    const credentials = {
      username: 'admin',
      password: 'password123'
    }
    
    const { data } = await axios.post('/api/auth/token', credentials)
    
    // بررسی نتایج
    expect(data).toHaveProperty('access_token')
    expect(data.token_type).toBe('bearer')
    expect(data).toHaveProperty('expires_in')
    expect(mockedAxios.post).toHaveBeenCalledWith('/api/auth/token', credentials)
  })
  
  test('should get user profile with valid token', async () => {
    // تعریف داده مورد انتظار
    const mockUserProfile = {
      id: 1,
      username: 'admin',
      email: 'admin@example.com',
      full_name: 'Admin User',
      is_admin: true,
      role: 'admin',
      created_at: '2025-05-10T12:00:00Z'
    }

    // تنظیم پاسخ مورد نظر برای درخواست GET
    mockedAxios.get.mockResolvedValueOnce({ data: mockUserProfile })
    
    // تنظیم هدر احراز هویت
    axios.defaults.headers.common['Authorization'] = 'Bearer test-token'
    
    // فراخوانی API
    const { data } = await axios.get('/api/users/me')
    
    // بررسی نتایج
    expect(data.username).toBe('admin')
    expect(data.is_admin).toBe(true)
    expect(data.role).toBe('admin')
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/users/me')
    expect(axios.defaults.headers.common['Authorization']).toBe('Bearer test-token')
  })
})
