// Global type declarations for the project

// React
declare module 'react' {
  export default any;
  export * from 'react';
}

declare module 'react/jsx-runtime' {
  export default any;
  export * from 'react/jsx-runtime';
}

// React Router
declare module 'react-router-dom' {
  export const BrowserRouter: any;
  export const Routes: any;
  export const Route: any;
  export const Link: any;
  export const Navigate: any;
  export const useNavigate: () => (path: string) => void;
  export const useLocation: () => { pathname: string; search: string; hash: string; state: any };
  export const useParams: () => Record<string, string>;
}

// کلاس‌های utility برای Tailwind CSS
declare module '@/lib/utils' {
  export function cn(...inputs: any[]): string;
}

// UI Components
declare module '@/components/ui/button' {
  export const Button: any;
}

declare module '@/components/ui/card' {
  export const Card: any;
  export const CardHeader: any;
  export const CardTitle: any;
  export const CardDescription: any;
  export const CardContent: any;
  export const CardFooter: any;
}

declare module '@/components/ui/toast' {
  export const Toast: any;
  export const ToastProvider: any;
  export const ToastViewport: any;
  export const ToastAction: any;
  export const ToastClose: any;
  export const ToastTitle: any;
  export const ToastDescription: any;
  export const useToast: () => {
    toast: (props: any) => void;
    dismiss: (toastId?: string) => void;
  };
}

// تعریف انواع وضعیت
interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
}

interface ApiResponse<T> {
  data?: T;
  error?: string;
  success: boolean;
}

interface Activity {
  id: string;
  user_id: string;
  type: string;
  description: string;
  created_at: string;
}

interface Stat {
  name: string;
  value: number;
  change: number;
}
