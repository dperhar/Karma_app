import { type FC, type MouseEventHandler, type JSX, useCallback } from 'react';
import { type LinkProps as NextLinkProps, default as NextLink } from 'next/link';
import { clsx } from 'clsx';

import './styles.css';

export interface LinkProps extends NextLinkProps, Omit<JSX.IntrinsicElements['a'], 'href'> {
}

export const Link: FC<LinkProps> = ({
  className,
  onClick: propsOnClick,
  href,
  ...rest
}) => {
  const onClick = useCallback<MouseEventHandler<HTMLAnchorElement>>((e) => {
    propsOnClick?.(e);

    // No need to intercept clicks, let the browser handle them.
    // External links will open in a new tab by default if target="_blank" is used.
    
  }, [href, propsOnClick]);

  return (
    <NextLink
      {...rest}
      href={href}
      onClick={onClick}
      className={clsx(className, 'link')}
    />
  );
};
