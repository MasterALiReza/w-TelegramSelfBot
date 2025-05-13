/// <reference types="react" />
/// <reference types="react-dom" />

// تنظیمات برای حل مشکلات JSX
declare namespace JSX {
  interface Element extends React.ReactElement<any, any> { }
  interface IntrinsicElements {
    [elemName: string]: any;
  }
  interface ElementAttributesProperty {
    props: Record<string, unknown>;
  }
  interface ElementChildrenAttribute {
    children: Record<string, unknown>;
  }
}

// حل مشکل مربوط به فایل‌های استاتیک
declare module '*.svg' {
  import * as React from 'react';
  export const ReactComponent: React.FunctionComponent<React.SVGProps<SVGSVGElement>>;
  const src: string;
  export default src;
}

declare module '*.jpg' {
  const src: string;
  export default src;
}

declare module '*.jpeg' {
  const src: string;
  export default src;
}

declare module '*.png' {
  const src: string;
  export default src;
}

declare module '*.gif' {
  const src: string;
  export default src;
}

declare module '*.webp' {
  const src: string;
  export default src;
}

// برای فایل‌های استایل
declare module '*.css' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module '*.scss' {
  const classes: { readonly [key: string]: string };
  export default classes;
}

// برای environment
interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL: string;
  readonly VITE_SUPABASE_ANON_KEY: string;
  readonly VITE_API_URL: string;
}
