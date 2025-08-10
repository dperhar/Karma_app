import type { FC, JSX } from 'react';
import { clsx } from 'clsx';

import './styles.css';

// Re-define the RGB type locally to remove SDK dependency
type RGBType = `#${string}`;

export type RGBProps = JSX.IntrinsicElements['div'] & {
  color: RGBType;
};

export const RGB: FC<RGBProps> = ({ color, className, ...rest }) => (
  <span {...rest} className={clsx('rgb', className)}>
    <i className='rgb__icon' style={{ backgroundColor: color }}/>
    {color}
  </span>
);
