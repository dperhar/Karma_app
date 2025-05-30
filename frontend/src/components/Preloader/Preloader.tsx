import { type FC } from 'react';
import styles from './styles.module.css';

export const Preloader: FC = () => {
  return (
    <div className={styles.preloader}>
      {/* Outer rotating element */}
      <div className={styles.circle}>
        <svg width="100" height="100" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="50" cy="50" r="45" stroke="#8774E1" strokeWidth="8" strokeLinecap="round" strokeDasharray="283" strokeDashoffset="100" />
        </svg>
      </div>
      
      {/* Inner Telegram paper airplane icon */}
      <div className={styles.inner}>
        <svg width="60" height="60" viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
          {/* Dark background circle */}
          <circle cx="30" cy="30" r="30" fill="#202A39" />
          
          {/* Telegram paper airplane icon */}
          <path 
            d="M44 19L14 29L24 33L28 43L44 19Z" 
            fill="#0088CC" 
            stroke="#8774E1" 
            strokeWidth="1.5" 
            strokeLinejoin="round"
          />
          <path 
            d="M24 33L44 19L28 43" 
            fill="#0088CC" 
            stroke="#8774E1" 
            strokeWidth="1.5" 
            strokeLinejoin="round"
          />
          
          {/* Small glowing dots for trailing effect */}
          <circle cx="24" cy="33" r="1.5" fill="#8774E1" opacity="0.8" />
          <circle cx="22" cy="32" r="1" fill="#8774E1" opacity="0.6" />
          <circle cx="20" cy="31" r="0.8" fill="#8774E1" opacity="0.4" />
          <circle cx="18" cy="30" r="0.6" fill="#8774E1" opacity="0.2" />
        </svg>
      </div>
    </div>
  );
}; 