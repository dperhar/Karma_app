import { FC } from 'react';

import { AIDialogResponse } from '@/types/ai';
import { AIDialogItem } from './AIDialogItem';

interface AIDialogListProps {
  dialogs: AIDialogResponse[];
  onDialogClick: (dialog: AIDialogResponse) => void;
  selectedDialogId?: string;
}

export const AIDialogList: FC<AIDialogListProps> = ({ 
  dialogs, 
  onDialogClick, 
  selectedDialogId 
}) => {
  if (dialogs.length === 0) {
    return (
      <div className="alert alert-info">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" className="stroke-current shrink-0 w-6 h-6">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
        </svg>
        <span>No AI dialogs found. Create a new one to get started.</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {dialogs.map((dialog) => (
        <AIDialogItem
          key={dialog.id}
          dialog={dialog}
          onClick={onDialogClick}
          isSelected={selectedDialogId === dialog.id}
        />
      ))}
    </div>
  );
}; 