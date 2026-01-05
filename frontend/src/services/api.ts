import axios from 'axios';
import { ApiResponse } from '@/types/chat';

const API_BASE_URL = 'http://localhost:8001';

export async function sendChatMessage(
  message: string,
  sessionId?: string,
  file?: File
): Promise<ApiResponse> {
  const formData = new FormData();
  formData.append('message', message);
  
  if (sessionId) {
    formData.append('session_id', sessionId);
  }
  
  if (file) {
    formData.append('file', file);
  }

  const response = await axios.post<ApiResponse>(`${API_BASE_URL}/chat`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
}
