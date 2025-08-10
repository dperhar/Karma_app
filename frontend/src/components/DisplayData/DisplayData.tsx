import type { FC, ReactNode } from 'react';

import { RGB } from '@/components/RGB/RGB';
import { Link } from '@/components/Link/Link';

import './styles.css';

// Custom type guard to check for RGB color string
function isRGB(value: any): value is `#${string}` {
  return typeof value === 'string' && /^#([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$/.test(value);
}

export type DisplayDataRow =
  & { title: string }
  & (
  | { type: 'link'; value?: string }
  | { value: ReactNode }
  )

export interface DisplayDataProps {
  header?: ReactNode;
  footer?: ReactNode;
  rows: DisplayDataRow[];
}

export const DisplayData: FC<DisplayDataProps> = ({ header, rows }) => (
  <div className="display-data-section">
    {header && <div className="display-data-header">{header}</div>}
    {rows.map((item, idx) => {
      let valueNode: ReactNode;

      if (item.value === undefined) {
        valueNode = <i>empty</i>;
      } else {
        if ('type' in item) {
          valueNode = <Link href={item.value}>Open</Link>;
        } else if (typeof item.value === 'string') {
          valueNode = isRGB(item.value)
            ? <RGB color={item.value}/>
            : item.value;
        } else if (typeof item.value === 'boolean') {
          valueNode = <input type="checkbox" checked={item.value} disabled />;
        } else {
          valueNode = item.value;
        }
      }

      return (
        <div
          className='display-data__line'
          key={idx}
        >
          <div className="display-data__line-title">{item.title}</div>
          <span className='display-data__line-value'>
            {valueNode}
          </span>
        </div>
      );
    })}
  </div>
);
