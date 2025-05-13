import * as React from 'react';

export interface ToastProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'destructive' | 'success';
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
}

export type ToastActionElement = React.ReactElement;

export interface ToastState {
  id: string;
  title?: React.ReactNode;
  description?: React.ReactNode;
  action?: ToastActionElement;
  variant?: 'default' | 'destructive' | 'success';
  open: boolean;
  onOpenChange?: (open: boolean) => void;
}
