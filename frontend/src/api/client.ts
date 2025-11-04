import axios from 'axios';
import { SearchRequest, SearchResponse } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8001';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const searchAPI = {
  search: async (params: SearchRequest): Promise<SearchResponse> => {
    const response = await apiClient.get('/api/v1/search/', { params });
    return response.data;
  },

  health: async (): Promise<{ status: string; timestamp: string }> => {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export default apiClient;
