import { http, HttpResponse } from 'msw'

// تعریف هندلرهای mock برای API
export const handlers = [
  // احراز هویت
  http.post('/api/auth/token', () => {
    return HttpResponse.json(
      {
        access_token: 'test-token',
        token_type: 'bearer',
        expires_in: 3600
      },
      { status: 200 }
    )
  }),
  
  // دریافت اطلاعات کاربر
  http.get('/api/users/me', () => {
    return HttpResponse.json(
      {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        full_name: 'Admin User',
        is_admin: true,
        role: 'admin',
        created_at: '2025-05-10T12:00:00Z'
      },
      { status: 200 }
    )
  }),
  
  // دریافت لیست پلاگین‌ها
  http.get('/api/plugins', () => {
    return HttpResponse.json(
      [
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
      ],
      { status: 200 }
    )
  }),
  
  // نصب پلاگین
  http.post('/api/plugins/install', () => {
    return HttpResponse.json(
      {
        id: 3,
        name: 'New Plugin',
        version: '1.0.0',
        description: 'Newly installed plugin',
        author: 'Test Author',
        category: 'tools',
        is_enabled: true,
        config: '{}'
      },
      { status: 201 }
    )
  }),
  
  // تغییر وضعیت پلاگین
  http.patch('/api/plugins/:id', async ({ params, request }) => {
    const id = params.id
    const body = await request.json() as { is_enabled: boolean }
    return HttpResponse.json(
      {
        id: Number(id),
        is_enabled: body.is_enabled
      },
      { status: 200 }
    )
  }),
  
  // حذف پلاگین
  http.delete('/api/plugins/:id', () => {
    return new HttpResponse(null, { status: 204 })
  }),
  
  // دریافت آمارها
  http.get('/api/stats/summary', () => {
    return HttpResponse.json(
      {
        total_users: 10,
        total_plugins: 5,
        active_plugins: 3,
        total_messages: 1000,
        daily_messages: 100,
        bot_status: 'online',
        last_activity: '2025-05-13T01:30:00Z'
      },
      { status: 200 }
    )
  }),
  
  // دریافت فعالیت‌های اخیر
  http.get('/api/activities/recent', () => {
    return HttpResponse.json(
      [
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
      ],
      { status: 200 }
    )
  }),
  
  // دریافت منابع سیستم
  http.get('/api/system/resources', () => {
    return HttpResponse.json(
      {
        cpu_usage: 25,
        memory_usage: 512,
        memory_total: 4096,
        disk_usage: 10240,
        disk_total: 102400
      },
      { status: 200 }
    )
  })
]
