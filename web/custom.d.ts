// تعریف JSX برای اطمینان از اینکه تمامی المان‌های HTML شناخته شده هستند
declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
