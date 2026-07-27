export function BellIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M12 2.5C10.34 2.5 9 3.84 9 5.5V5.9C6.67 6.79 5 9.15 5 11.9V16.5L3 18.5V19.5H21V18.5L19 16.5V11.9C19 9.15 17.33 6.79 15 5.9V5.5C15 3.84 13.66 2.5 12 2.5Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path
        d="M9.5 21.5C9.5 22.6 10.62 23.5 12 23.5C13.38 23.5 14.5 22.6 14.5 21.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function UsersIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="9" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3.5 19c0-3 2.5-5 5.5-5s5.5 2 5.5 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M16 5.2A3 3 0 0 1 16 11M17.5 19c0-2.3-1-4-2.6-5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function CalendarIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="3.5" y="5" width="17" height="15" rx="2.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3.5 9.5h17M8 3v4M16 3v4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function BagIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M6 8h12l-1 11a2 2 0 0 1-2 1.8H9A2 2 0 0 1 7 19L6 8Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M9 8V6.5a3 3 0 0 1 6 0V8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function MegaphoneIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M4 10v4a1.5 1.5 0 0 0 1.5 1.5H7l1 4h2l-1-4 8 3.5V6L9 9.5H5.5A1.5 1.5 0 0 0 4 11Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M18 9.5a3 3 0 0 1 0 5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function ChevronRightIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M9 5l7 7-7 7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function HeartIcon({ className, filled = false }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill={filled ? "currentColor" : "none"}
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M12 20s-7-4.35-9.3-8.4C1.2 8.9 2.5 5.8 5.5 5.2c1.9-.38 3.6.62 4.5 2 .9-1.38 2.6-2.38 4.5-2 3 .6 4.3 3.7 2.8 6.4C19 15.65 12 20 12 20Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function TagIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M4 4h7l9 9-7 7-9-9V4Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <circle cx="8.5" cy="8.5" r="1.4" fill="currentColor" />
    </svg>
  );
}

export function CreditCardIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="3" y="5.5" width="18" height="13" rx="2.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M3 9.5h18" stroke="currentColor" strokeWidth="1.6" />
      <path d="M6.5 14.5h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function RefreshIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M20 11a8 8 0 0 0-14-4.5M4 5v4h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M4 13a8 8 0 0 0 14 4.5M20 19v-4h-4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function GiftIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="4" y="9" width="16" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M4 13h16M12 9v11" stroke="currentColor" strokeWidth="1.6" />
      <path d="M12 9S10.5 5 8.5 5A2 2 0 0 0 8 9M12 9s1.5-4 3.5-4A2 2 0 0 1 16 9" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function CheckCircleIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M8.5 12.2l2.3 2.3 4.7-4.9" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function ChatIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M4 5.5h16v11H9l-4 3.5v-3.5H4v-11Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  );
}

export function ClipboardIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect x="5" y="5" width="14" height="16" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M9 5a3 3 0 0 1 6 0" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M8.5 11h7M8.5 15h5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function CartIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M3 4h2l2.2 11.2a1.5 1.5 0 0 0 1.5 1.2h8.1a1.5 1.5 0 0 0 1.5-1.2L21 7H6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="9.5" cy="19.5" r="1.4" fill="currentColor" />
      <circle cx="17.5" cy="19.5" r="1.4" fill="currentColor" />
    </svg>
  );
}

export function TrashIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M4 6.5h16M9 6.5V5a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 5v1.5M6.5 6.5l.8 12a2 2 0 0 0 2 1.9h5.4a2 2 0 0 0 2-1.9l.8-12" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M10 10.5v6M14 10.5v6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function ChevronDownIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M5 9l7 7 7-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function SearchIcon({ className }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" strokeWidth="1.6" />
      <line x1="20" y1="20" x2="15.8" y2="15.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function PencilIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path
        d="M4 20h4L19.5 8.5a2.1 2.1 0 0 0-3-3L5 17v3Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M14.5 7 17 9.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function ArrowLeftIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <path d="M19 12H5M11 6l-6 6 6 6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* 聯絡平台品牌圖示：依圖 06 為圓形實心品牌色，故不使用 currentColor。 */

export function FacebookIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="12" cy="12" r="12" fill="#1877F2" />
      <path
        d="M15.6 12.4h-2.2V19h-2.8v-6.6H9v-2.4h1.6V8.4c0-1.9 1.1-3.1 3.2-3.1h2v2.4h-1.3c-.8 0-1 .3-1 .9v1.4h2.4l-.3 2.4Z"
        fill="#fff"
      />
    </svg>
  );
}

export function DiscordIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="12" cy="12" r="12" fill="#5865F2" />
      <path
        d="M16.6 8.1a9.6 9.6 0 0 0-2.4-.7l-.3.6c-.9-.1-1.8-.1-2.6 0l-.3-.6c-.9.1-1.7.4-2.5.7-1.5 2.2-1.9 4.4-1.7 6.5a9.8 9.8 0 0 0 3 1.5l.6-1c-.3-.1-.7-.3-1-.5l.2-.2a6.9 6.9 0 0 0 5.9 0l.2.2c-.3.2-.6.4-1 .5l.6 1c1.1-.3 2.1-.8 3-1.5.3-2.4-.4-4.6-1.7-6.5Zm-6.3 5.2c-.6 0-1.1-.5-1.1-1.2s.5-1.2 1.1-1.2c.6 0 1.1.5 1.1 1.2s-.5 1.2-1.1 1.2Zm3.4 0c-.6 0-1.1-.5-1.1-1.2s.5-1.2 1.1-1.2c.6 0 1.1.5 1.1 1.2s-.5 1.2-1.1 1.2Z"
        fill="#fff"
      />
    </svg>
  );
}

export function LineIcon({ className }) {
  return (
    <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <circle cx="12" cy="12" r="12" fill="#06C755" />
      <path
        d="M12 5.2c-3.9 0-7 2.5-7 5.6 0 2.8 2.5 5.1 5.9 5.5.2 0 .5.2.6.4.1.2 0 .5 0 .7l-.1.6c0 .2-.1.7.6.4 1.7-.7 4.2-2.4 5.4-4.1.8-.9 1.2-1.9 1.2-3.5 0-3.1-3.1-5.6-6.6-5.6Zm-2.6 7.4H8c-.2 0-.3-.1-.3-.3V9.9c0-.2.1-.3.3-.3s.3.1.3.3v2.1h1.1c.2 0 .3.1.3.3s-.1.3-.3.3Zm1.3-.3c0 .2-.1.3-.3.3s-.3-.1-.3-.3V9.9c0-.2.1-.3.3-.3s.3.1.3.3v2.4Zm2.9 0c0 .1-.1.3-.2.3h-.1c-.1 0-.2 0-.2-.1l-1.1-1.5v1.3c0 .2-.1.3-.3.3s-.3-.1-.3-.3V9.9c0-.1.1-.3.2-.3h.1c.1 0 .2 0 .2.1l1.1 1.5V9.9c0-.2.1-.3.3-.3s.3.1.3.3v2.4Zm2-1.5c.2 0 .3.1.3.3s-.1.3-.3.3h-1.1v.6h1.1c.2 0 .3.1.3.3s-.1.3-.3.3h-1.4c-.2 0-.3-.1-.3-.3V9.9c0-.2.1-.3.3-.3h1.4c.2 0 .3.1.3.3s-.1.3-.3.3h-1.1v.6h1.1Z"
        fill="#fff"
      />
    </svg>
  );
}
