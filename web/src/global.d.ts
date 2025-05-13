// Global type declarations

// اعلان مدول‌ها برای حل مشکل "cannot find module"
declare module 'react' {
  export = React;
}

declare module 'react/jsx-runtime' {
  export const jsx: any;
  export const jsxs: any;
  export const Fragment: React.ReactFragment;
}

declare module 'react-router-dom' {
  export const BrowserRouter: React.FC<{ children: React.ReactNode }>;
  export const Routes: React.FC<{ children: React.ReactNode }>;
  export const Route: React.FC<{
    path: string;
    element: React.ReactNode;
    index?: boolean;
  }>;
  export const Link: React.FC<{
    to: string;
    className?: string;
    children: React.ReactNode;
    [key: string]: any;
  }>;
  export const Navigate: React.FC<{ to: string; replace?: boolean }>;
  export function useNavigate(): (path: string, options?: { replace?: boolean } | undefined) => void;
  export function useLocation(): {
    pathname: string;
    search: string;
    hash: string;
    state: any;
  };
  export function useParams<T extends Record<string, string | undefined>>(): T;
}

// تایپ‌های API
interface ApiResponse<T = any> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}

interface User {
  id: string;
  username: string;
  email: string;
  created_at: string;
  updated_at: string;
}

interface Activity {
  id: string;
  user_id: string;
  type: string;
  description: string;
  created_at: string;
}

// برای آداپتور JSX
interface JSX {
  IntrinsicElements: {
    [elemName: string]: any;
  };
}
