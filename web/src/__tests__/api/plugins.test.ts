/**
 * @jest-environment jsdom
 */

import axios from 'axios'
import { describe, test, expect, jest, beforeEach } from '@jest/globals'

// Mock کردن axios
jest.mock('axios')
const mockedAxios = axios as jest.Mocked<typeof axios>

describe('Plugins API', () => {
  beforeEach(() => {
    jest.resetAllMocks()
  })

  test('should fetch plugins successfully', async () => {
    // تعریف داده مورد انتظار
    const mockPlugins = [
      {
        id: 1,
        name: 'Plugin 1',
        version: '1.0.0',
        description: 'Test plugin 1',
        author: 'Test Author',
        category: 'tools',
        is_enabled: true,
        config: JSON.stringify({ setting1: 'value1' })
      },
      {
        id: 2,
        name: 'Plugin 2',
        version: '1.0.0',
        description: 'Test plugin 2',
        author: 'Test Author',
        category: 'security',
        is_enabled: false,
        config: JSON.stringify({ setting2: 'value2' })
      }
    ]

    // تنظیم پاسخ مورد نظر برای درخواست GET
    mockedAxios.get.mockResolvedValueOnce({ data: mockPlugins })
    
    // فراخوانی API
    const { data } = await axios.get('/api/plugins')
    
    // بررسی نتایج
    expect(data).toHaveLength(2)
    expect(data[0].name).toBe('Plugin 1')
    expect(data[1].name).toBe('Plugin 2')
    expect(mockedAxios.get).toHaveBeenCalledWith('/api/plugins')
  })

  test('should install a new plugin', async () => {
    // تعریف داده مورد انتظار
    const mockNewPlugin = {
      id: 3,
      name: 'New Plugin',
      version: '1.0.0',
      description: 'Newly installed plugin',
      author: 'Test Author',
      category: 'tools',
      is_enabled: true,
      config: '{}'
    }

    // تنظیم پاسخ مورد نظر برای درخواست POST
    mockedAxios.post.mockResolvedValueOnce({ 
      data: mockNewPlugin, 
      status: 201 
    })
    
    // فراخوانی API
    const pluginUrl = 'https://example.com/plugin.zip'
    const { data, status } = await axios.post('/api/plugins/install', { url: pluginUrl })
    
    // بررسی نتایج
    expect(status).toBe(201)
    expect(data.name).toBe('New Plugin')
    expect(data.is_enabled).toBe(true)
    expect(mockedAxios.post).toHaveBeenCalledWith('/api/plugins/install', { url: pluginUrl })
  })

  test('should toggle plugin status', async () => {
    // تعریف داده مورد انتظار
    const pluginId = 1
    const newStatus = false
    const mockResponse = {
      id: pluginId,
      is_enabled: newStatus
    }

    // تنظیم پاسخ مورد نظر برای درخواست PATCH
    mockedAxios.patch.mockResolvedValueOnce({ data: mockResponse })
    
    // فراخوانی API
    const { data } = await axios.patch(`/api/plugins/${pluginId}`, {
      is_enabled: newStatus
    })
    
    // بررسی نتایج
    expect(data.id).toBe(pluginId)
    expect(data.is_enabled).toBe(newStatus)
    expect(mockedAxios.patch).toHaveBeenCalledWith(`/api/plugins/${pluginId}`, {
      is_enabled: newStatus
    })
  })

  test('should delete a plugin', async () => {
    // تعریف داده مورد انتظار
    const pluginId = 2

    // تنظیم پاسخ مورد نظر برای درخواست DELETE
    mockedAxios.delete.mockResolvedValueOnce({ status: 204 })
    
    // فراخوانی API
    const { status } = await axios.delete(`/api/plugins/${pluginId}`)
    
    // بررسی نتایج
    expect(status).toBe(204)
    expect(mockedAxios.delete).toHaveBeenCalledWith(`/api/plugins/${pluginId}`)
  })
})
