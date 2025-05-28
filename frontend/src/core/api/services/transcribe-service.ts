import { APIResponse } from '@/types/api';
import { TranscribeResponse } from '@/types/transcribe';
import { ApiClient } from '../api-client';

export class TranscribeService extends ApiClient {
  private readonly endpoint = '/transcribe';

  constructor() {
    super();
    console.log('TranscribeService initialized with endpoint:', this.endpoint);
  }

  async transcribe_audio(file: File, initDataRaw?: string): Promise<APIResponse<TranscribeResponse>> {
    console.log('transcribe_audio called');
    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await this.request<APIResponse<TranscribeResponse>>(
        this.endpoint,
        {
          method: 'POST',
          body: formData,
          headers: {
            'Accept': 'application/json'
          }
        },
        initDataRaw
      );
      
      console.log('transcribe_audio response:', response);
      return response;
    } catch (error) {
      console.error('Failed to transcribe audio:', error);
      throw error;
    }
  }
}

export const transcribeService = new TranscribeService(); 