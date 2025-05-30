import { format } from 'date-fns';
import { FC } from 'react';

import { AIDialogResponse } from '@/types/ai';

interface AIDialogItemProps {
  dialog: AIDialogResponse;
  onClick: (dialog: AIDialogResponse) => void;
  isSelected: boolean;
}

export const AIDialogItem: FC<AIDialogItemProps> = ({ dialog, onClick, isSelected }) => {
  // Format the creation date
  const formattedDate = format(new Date(dialog.created_at), 'dd.MM.yyyy HH:mm');
  
  return (
    <div 
      className={`card card-compact cursor-pointer hover:bg-base-200 transition-colors duration-200 mb-2 ${isSelected ? 'bg-primary bg-opacity-10 border border-primary' : 'bg-base-100'}`}
      onClick={() => onClick(dialog)}
    >
      <div className="card-body">
        <div className="flex justify-between items-center">
          <h3 className="card-title text-base">
            AI Dialog #{dialog.id.substring(0, 8)}
          </h3>
          <span className="text-xs opacity-70">{formattedDate}</span>
        </div>
      </div>
    </div>
  );
}; 