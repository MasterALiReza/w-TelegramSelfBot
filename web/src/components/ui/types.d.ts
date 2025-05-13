// تعریف تایپ‌های کامپوننت‌های UI

// تعریف تایپ‌های مشترک
type ComponentWithRef<T, P = Record<string, unknown>> = React.ForwardRefExoticComponent<
  React.PropsWithoutRef<P> & React.RefAttributes<T>
>;

// تایپ‌های مربوط به کارت
export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}
export interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {}
export interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {}
export interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {}
export interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {}
export interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {}

// تایپ‌های مربوط به دکمه
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link';
  size?: 'default' | 'sm' | 'lg' | 'icon';
}

// تایپ‌های مربوط به toast
export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive' | 'success';
}

export interface ToastActionProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}
export interface ToastProviderProps {
  children: React.ReactNode;
}
export interface ToastViewportProps extends React.HTMLAttributes<HTMLOListElement> {}
export interface ToastTitleProps extends React.HTMLAttributes<HTMLDivElement> {}
export interface ToastDescriptionProps extends React.HTMLAttributes<HTMLDivElement> {}

export interface UseToastResult {
  toast: (props: any) => void;
  dismiss: (toastId?: string) => void;
}
