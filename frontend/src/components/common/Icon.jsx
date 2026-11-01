import React from 'react';

const icons = {
  drop: (
    <path d="M12 3s6 6.2 6 10.5A6 6 0 0 1 6 13.5C6 9.2 12 3 12 3z" />
  ),
  truck: (
    <>
      <path d="M3 6h11v10H3zM14 9h4l3 3v4h-7" />
      <circle cx="7" cy="17.5" r="1.8" />
      <circle cx="17" cy="17.5" r="1.8" />
    </>
  ),
  shop: (
    <path d="M4 9l1.5-5h13L20 9M4 9v11h16V9M4 9c0 1.7 1.3 3 2.7 3S9.300 10.700 9.300 9c0 1.700 1.300 3 2.700 3s2.700-1.300 2.700-3c0 1.700 1.300 3 2.700 3S20 10.700 20 9" />
  ),
  shield: (
    <>
      <path d="M12 3l7 3v5c0 4.500-3 8-7 10-4-2-7-5.500-7-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
  bell: (
    <>
      <path d="M6 16V11a6 6 0 0 1 12 0v5l1.500 2h-15zM10 21h4" />
    </>
  ),
  pin: (
    <>
      <path d="M12 21s7-6 7-11a7 7 0 0 0-14 0c0 5 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.500" />
    </>
  ),
  leaf: (
    <>
      <path d="M5 19c0-9 5-14 15-14 0 10-5 15-14 15M5 19c2-5 5-8 9-10" />
    </>
  ),
  route: (
    <>
      <circle cx="6" cy="18" r="2.500" />
      <circle cx="18" cy="6" r="2.500" />
      <path d="M8.500 18H15a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h6.500" />
    </>
  ),
  check: (
    <path d="M5 12.500l4.500 4.500L19 7.500" />
  ),
  plus: (
    <path d="M12 5v14M5 12h14" />
  ),
  expand: (
    <path d="M14 4h6v6M10 20H4v-6M20 4l-7 7M4 20l7-7" />
  ),
  dl: (
    <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />
  ),
  spark: (
    <path d="M4 18l5-6 4 3 7-9M15 6h5v5" />
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </>
  ),
  batt: (
    <>
      <rect x="3" y="8" width="16" height="9" rx="2" />
      <path d="M21 11v3M7 11v3" />
    </>
  ),
  cloud: (
    <path d="M7 18a4 4 0 0 1-.5-8A6 6 0 0 1 18 11a3.500 3.500 0 0 1-.5 7z" />
  )
};

export function Icon({ name, className = '', style = {}, ...props }) {
  const content = icons[name] || null;
  return (
    <svg
      className={`i ${className}`.trim()}
      viewBox="0 0 24 24"
      aria-hidden="true"
      style={style}
      {...props}
    >
      {content}
    </svg>
  );
}

export const ShieldIcon = (props) => <Icon name="shield" {...props} />;
export const TruckIcon = (props) => <Icon name="truck" {...props} />;
export const ShopIcon = (props) => <Icon name="shop" {...props} />;
export const DropIcon = (props) => <Icon name="drop" {...props} />;
export const BellIcon = (props) => <Icon name="bell" {...props} />;
export const PinIcon = (props) => <Icon name="pin" {...props} />;
export const LeafIcon = (props) => <Icon name="leaf" {...props} />;
export const RouteIcon = (props) => <Icon name="route" {...props} />;
export const CheckIcon = (props) => <Icon name="check" {...props} />;
export const PlusIcon = (props) => <Icon name="plus" {...props} />;
export const ExpandIcon = (props) => <Icon name="expand" {...props} />;
export const DownloadIcon = (props) => <Icon name="dl" {...props} />;
export const SparkIcon = (props) => <Icon name="spark" {...props} />;
export const ClockIcon = (props) => <Icon name="clock" {...props} />;
export const BatteryIcon = (props) => <Icon name="batt" {...props} />;
export const CloudIcon = (props) => <Icon name="cloud" {...props} />;

export default Icon;
