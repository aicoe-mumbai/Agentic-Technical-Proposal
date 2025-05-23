import axios from 'axios';

// The backend URL, ensure this matches your running backend (port 8001 as configured)
const API_BASE_URL = 'http://localhost:8001/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptors can be added here for global error handling or token management if needed
// apiClient.interceptors.response.use(response => response, error => {
//   // Handle errors globally
//   return Promise.reject(error);
// });

// Template Endpoints
export const listTemplatesAPI = () => apiClient.get('/templates/');
export const getTemplateAPI = (projectName: string) => apiClient.get(`/templates/${projectName}`);
export const createTemplateAPI = (data: FormData) => apiClient.post('/templates/', data, {
  headers: { 'Content-Type': 'multipart/form-data' },
});
export const deleteTemplateAPI = (projectName: string) => apiClient.delete(`/templates/${projectName}`);
export const getTemplateDataAPI = (projectName: string) => apiClient.get(`/templates/${projectName}/data`);
export const updateTemplateAPI = (projectName: string, data: FormData) => apiClient.put(`/templates/${projectName}`, data, {
  headers: { 'Content-Type': 'multipart/form-data' }, // FormData is used for potential file upload
});

// Document Endpoints
export const listDocumentsAPI = () => apiClient.get('/documents/');
export const uploadDocumentAPI = (data: FormData) => apiClient.post('/documents/upload', data, {
  headers: { 'Content-Type': 'multipart/form-data' },
});
export const getDocumentStatusAPI = (filename: string) => apiClient.get(`/documents/${filename}/status`);
export const extractDocumentScopeAPI = (filename: string, cache: boolean = true) => apiClient.get(`/documents/${filename}/scope?cache=${cache}`);
export const confirmDocumentScopeAPI = (filename: string, pageNumbers: number[]) => apiClient.post(`/documents/${filename}/confirm-scope`, { page_numbers: pageNumbers });
export const saveDocumentTopicsAPI = (filename: string, templateName: string, topics: any[]) => apiClient.post(`/documents/${filename}/topics/${templateName}`, { topics }); // Body might need adjustment
export const getDocumentTopicsAPI = (filename: string, templateName: string) => apiClient.get(`/documents/${filename}/topics/${templateName}`);
export const extractPageTextAPI = (filename: string, pageRange: string) => apiClient.get(`/documents/${filename}/page/${pageRange}`);
export const queryDocumentAPI = (filename: string, query: string, history?: any[]) => apiClient.post(`/documents/${filename}/query`, { query, history });
export const rangeQueryDocumentAPI = (filename: string, query: string, page_start: number, page_end: number, history?: any[]) => apiClient.post(`/documents/${filename}/range-query`, { query, page_start, page_end, history });
export const saveDocumentContentAPI = (filename: string, topicId: number, content: string) => apiClient.post(`/documents/${filename}/content`, { topic_id: topicId, content });
export const saveDocumentContentBulkAPI = (filename: string, contents: Array<{ topic_id: number, content: string }>) => apiClient.post(`/documents/${filename}/content/bulk`, contents);
export const getDocumentContentAPI = (filename: string, topicId: number) => apiClient.get(`/documents/${filename}/content/${topicId}`);

// Analysis Endpoints
export const generateTopicsAPI = (documentName: string, templateName: string) => apiClient.post(`/analysis/generate-topics/${documentName}/${templateName}`);
export const generateContentAPI = (documentName: string, templateName: string, topic: string, context?: string) => apiClient.post(`/analysis/generate-content/${documentName}/${templateName}`, { topic, context }); // Request body was { topic, context }
export const chatWithDocumentAPI = (documentName: string, templateName: string, message: string, history: any[]) => apiClient.post(`/analysis/chat/${documentName}/${templateName}`, { message, history });

export default apiClient; 