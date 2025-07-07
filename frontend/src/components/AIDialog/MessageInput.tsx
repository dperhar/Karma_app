import { FC, FormEvent, useEffect, useRef, useState } from 'react';

import { transcribeService } from '@/core/api/services/transcribe-service';
import { useUserStore } from '@/store/userStore';
import { LangChainMessageRequest } from '@/types/ai';
import { AudioRecorder } from '@/utils/AudioRecorder';

// Default values if user preferences are not set
const DEFAULT_CONTEXT_SIZE = 10;
const DEFAULT_MODEL = "gpt-3.5-turbo";
const DEFAULT_MAX_TOKENS = 2000;

interface MessageInputProps {
  dialogId: string;
  onSendMessage: (dialogId: string, content: string) => Promise<void>;
  isFirstMessage?: boolean;
  disabled?: boolean;
}

export const MessageInput: FC<MessageInputProps> = ({ 
  dialogId, 
  onSendMessage, 
  isFirstMessage = false,
  disabled = false 
}) => {
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [recordingError, setRecordingError] = useState<string | null>(null);
  
  // Get user preferences from the user store
  const { user } = useUserStore();
  
  const audioRecorderRef = useRef<AudioRecorder | null>(null);
  
  // Initialize audio recorder
  useEffect(() => {
    audioRecorderRef.current = new AudioRecorder();
    
    return () => {
      // Clean up if recording is in progress when component unmounts
      if (audioRecorderRef.current?.getIsRecording()) {
        try {
          audioRecorderRef.current.stopRecording();
        } catch (error) {
          console.error('Error stopping recording on unmount:', error);
        }
      }
    };
  }, []);
  
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!message.trim() || disabled || isSending) {
      return;
    }
    
    try {
      setIsSending(true);
      
      // Use user preferences from the store, or defaults if not set
      const dialogContextLength = user?.preferred_message_context_size || DEFAULT_CONTEXT_SIZE;
      const modelName = user?.preferred_ai_model || DEFAULT_MODEL;
      
      console.log(`Using context size: ${dialogContextLength}, model: ${modelName}`);
      
      // Create message request object based on LangChainMessageRequest schema
      const messageRequest: LangChainMessageRequest = {
        dialog_id: dialogId,
        content: message.trim(),
        dialog_context_length: dialogContextLength,
        model_name: modelName,
        temperature: 0.5,
        prompt_template: "base_tg_prompt",
        max_tokens: DEFAULT_MAX_TOKENS
      };
      
      console.log("Sending message request:", messageRequest);
      
      // Send message - still using the existing interface for compatibility
      await onSendMessage(dialogId, message.trim());
      
      setMessage('');
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsSending(false);
    }
  };
  
  const handleStartRecording = async () => {
    try {
      setRecordingError(null);
      
      if (!audioRecorderRef.current) {
        audioRecorderRef.current = new AudioRecorder();
      }
      
      await audioRecorderRef.current.startRecording();
      setIsRecording(true);
    } catch (error) {
      console.error('Error starting recording:', error);
      setRecordingError('Could not access microphone. Please check your browser permissions.');
    }
  };
  
  const handleStopRecording = async () => {
    if (!audioRecorderRef.current) {
      return;
    }
    
    try {
      setIsRecording(false);
      setIsTranscribing(true);
      
      const audioBlob = await audioRecorderRef.current.stopRecording();
      
      // Create a File object from the Blob
      const audioFile = new File([audioBlob], 'recording.m4a', { type: 'audio/m4a' });
      
      // Send to transcription service
      const response = await transcribeService.transcribe_audio(audioFile, "mock_init_data_for_telethon");
      
      if (response.success && response.data) {
        // Append transcribed text to current message
        const transcribedText = response.data.text.trim();
        
        if (transcribedText) {
          if (message.trim()) {
            // If there's already text, add a space before appending
            setMessage(prev => `${prev.trim()} ${transcribedText}`);
          } else {
            setMessage(transcribedText);
          }
        } else {
          setRecordingError('Could not transcribe audio. Please try again or type your message.');
        }
      } else {
        setRecordingError('Transcription failed. Please try again or type your message.');
      }
    } catch (error) {
      console.error('Error processing recording:', error);
      setRecordingError('Error processing recording. Please try again.');
    } finally {
      setIsTranscribing(false);
    }
  };
  
  const isInputDisabled = disabled || isSending || isRecording || isTranscribing;
  
  // Determine placeholder text based on recording status and whether it's the first message
  const placeholderText = isRecording 
    ? "Recording audio..." 
    : isTranscribing 
      ? "Transcribing..." 
      : isFirstMessage 
        ? "Введите ваш запрос или промпт для AI..." 
        : "Type your message here...";
  
  return (
    <div className="w-full">
      {recordingError && (
        <div className="alert alert-error mb-2 py-2 text-sm">
          <svg xmlns="http://www.w3.org/2000/svg" className="stroke-current shrink-0 h-4 w-4" fill="none" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{recordingError}</span>
        </div>
      )}
      
      <form onSubmit={handleSubmit} className="w-full">
        <div className={`flex ${isFirstMessage ? 'flex-col' : 'items-center'} gap-2`}>
          {isFirstMessage ? (
            <div className="w-full mb-2">
              <label className="label">
                <span className="label-text font-medium text-base">Введите ваш запрос или промпт для AI</span>
              </label>
              <textarea
                placeholder={placeholderText}
                className="textarea textarea-bordered w-full h-32 resize-y"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                disabled={isInputDisabled}
              />
            </div>
          ) : (
            <input
              type="text"
              placeholder={placeholderText}
              className="input input-bordered flex-grow"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={isInputDisabled}
            />
          )}
          
          <div className={`flex ${isFirstMessage ? 'justify-between w-full' : ''} gap-2`}>
            {/* Voice recording button */}
            {isRecording ? (
              <button 
                type="button"
                className="btn btn-error"
                onClick={handleStopRecording}
                disabled={isTranscribing}
              >
                {isTranscribing ? (
                  <span className="loading loading-spinner loading-sm"></span>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z" />
                  </svg>
                )}
              </button>
            ) : (
              <button 
                type="button"
                className="btn btn-secondary"
                onClick={handleStartRecording}
                disabled={isInputDisabled || isTranscribing}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                </svg>
              </button>
            )}
            
            {/* Send button */}
            <button 
              type="submit" 
              className={`btn btn-primary ${isFirstMessage ? 'px-6' : ''}`}
              disabled={!message.trim() || isInputDisabled}
            >
              {isSending ? (
                <span className="loading loading-spinner loading-sm"></span>
              ) : (
                <>
                  {isFirstMessage && <span>Отправить запрос</span>}
                  <svg 
                    xmlns="http://www.w3.org/2000/svg" 
                    className="h-6 w-6" 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" 
                    />
                  </svg>
                </>
              )}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
} 